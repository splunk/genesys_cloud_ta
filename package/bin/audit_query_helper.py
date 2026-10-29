"""Audit Query input handler."""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    AUDIT_QUERY_COMPLETED_STATUSES,
    DEFAULT_MAX_POLL_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    MAX_PAGE_SIZE,
    SOURCETYPE_OPERATIONAL_AUDITS,
)
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)
from genesys_cloud_ta.time_utils import exceed_range
from genesys_cloud_ta.validators import (
    validate_date,
)


def validate_input(definition: smi.ValidationDefinition):
    validate_date(definition.parameters.get("start_date"))


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        try:
            session_key = inputs.metadata["session_key"]
            configure_logger(logger, session_key)

            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "audit_query_checkpointer",
                session_key,
                ADDON_NAME,
            )

            proxy_config = get_proxy_configuration(logger, session_key)
            if proxy_config is None:
                continue

            log.modular_input_start(logger, normalized_input_name)

            account_region = get_account_property(
                session_key, input_item.get("account"), "region"
            )
            client_id = get_account_property(
                session_key, input_item.get("account"), "client_id"
            )
            client_secret = get_account_property(
                session_key, input_item.get("account"), "client_secret"
            )

            max_polls = int(
                input_item.get("max_poll_attempts", DEFAULT_MAX_POLL_ATTEMPTS)
            )
            poll_sleep = int(
                input_item.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
            )

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            checkpointer_key_name = normalized_input_name

            # Setting a default start date of 7 days ago from now
            now = datetime.now(timezone.utc)
            fallback_start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            start_date = input_item.get("start_date")
            if start_date is not None:
                fallback_start = datetime.strptime(start_date, "%Y-%m-%d").strftime(  # noqa: DTZ007
                    "%Y-%m-%dT%H:%M:%SZ"
                )

            start_time = kvstore_checkpointer.get(checkpointer_key_name)
            end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Evaluating the interval. It can be no greater than 31 days.
            # [400] BadRequest - You must specify a search interval as part of your query that does not exceed 31 days.
            if start_time is None or (
                start_time and exceed_range(start_time, end_time)
            ):
                logger.info(
                    f"Checkpoint not found or exceeds interval range of 31 days [{start_time}]. Using the configured start_date as fallback [{fallback_start}]."
                )
                start_time = fallback_start
                if exceed_range(fallback_start, end_time):
                    # This case keeps the system running in case of too far away in time checkpoint.
                    reset_start = (now - timedelta(days=7)).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                    logger.warning(
                        f"Fallback start_date exceeds interval range of 31 days. Resetting it to {reset_start}."
                    )
                    start_time = reset_start

            interval = f"{start_time}/{end_time}"

            body = {"interval": interval}
            logger.debug(f"Request body: {body}")

            response = client.post(
                "AuditApi", "post_audits_query", "AuditQueryRequest", body
            )
            if not response:
                raise RuntimeError(
                    "No response was received from the audit POST request. Please verify the request parameters and try again."
                )
            if len(response) > 1:
                logger.warning(
                    f"AuditApi call returned too many responses: {len(response)}"
                )

            transaction_id = response[0].id
            status = ""

            for _ in range(max_polls):
                state_resp = client.get(
                    "AuditApi", "get_audits_query_transaction_id", transaction_id
                )
                if not state_resp:
                    raise RuntimeError(
                        f"Failed to get status for transaction {transaction_id}"
                    )
                status = state_resp[0].state
                if status in AUDIT_QUERY_COMPLETED_STATUSES:
                    logger.debug(f"Audit complete with status '{status}'")
                    break
                time.sleep(poll_sleep)

            if status != "Succeeded":
                raise RuntimeError(f"Audit did not complete successfully: {status}")

            params = {
                "transaction_id": transaction_id,
                "allow_redirect": True,
                "page_size": MAX_PAGE_SIZE,
            }

            results = client.get(
                "AuditApi", "get_audits_query_transaction_id_results", **params
            )
            event_counter = 0

            for entity in results:
                if not isinstance(entity, dict):
                    value = entity.to_dict()
                    time_value = entity.event_date.timestamp()
                else:
                    # Retrieved via download URL file
                    value = entity
                    time_value = (
                        datetime.strptime(entity["eventTime"], "%Y-%m-%dT%H:%M:%SZ")
                        .replace(tzinfo=timezone.utc)
                        .timestamp()
                    )
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(value, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE_OPERATIONAL_AUDITS,
                        time=time_value,
                    )
                )
                event_counter += 1

            # Update checkpoint with the interval end in ISO8601 to keep next run contiguous
            if event_counter > 0:
                logger.debug(f"Indexed '{event_counter}' events")
                logger.debug(f"Updating checkpointer to {end_time}")
                kvstore_checkpointer.update(checkpointer_key_name, end_time)

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_OPERATIONAL_AUDITS,
                event_counter,
                input_item.get("index"),
                account=input_item.get("account"),
            )

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:  # noqa: BLE001
            log.log_exception(
                logger,
                e,
                "IngestionError",
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}",
            )

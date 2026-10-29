"""Organisation Usage input handler."""

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
    DEFAULT_MAX_POLL_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    SOURCETYPE_OPERATIONAL_USAGE_ORG,
)
from genesys_cloud_ta.time_utils import (
    get_interval_str,
    get_start_date,
    to_epoch,
)
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            configure_logger(logger, session_key)
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "org_usage_checkpointer",
                session_key,
                ADDON_NAME,
            )
            proxy_config = get_proxy_configuration(logger, session_key)
            if proxy_config is None:
                continue

            log.modular_input_start(logger, normalized_input_name)

            client_id = get_account_property(
                session_key, input_item.get("account"), "client_id"
            )
            client_secret = get_account_property(
                session_key, input_item.get("account"), "client_secret"
            )
            account_region = get_account_property(
                session_key, input_item.get("account"), "region"
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
            now = datetime.now(timezone.utc)
            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)
            start_date = get_start_date(to_epoch(current_checkpoint), now)

            body = {
                "interval": get_interval_str(start_date, now),
                "granularity": "Day",
            }

            job_response = client.post(
                "UsageApi",
                "post_usage_aggregates_query_jobs",
                "OrganizationPublicApiUsageQueryRequest",
                body,
            )

            logger.info("Fetching usage aggregates events.")

            results = []
            if job_response:
                # client.post() always returns a list of API responses; the submit
                # job endpoint returns a single object, so take the first element.
                job_obj = (
                    job_response[0] if isinstance(job_response, list) else job_response
                )
                job_dict = (
                    job_obj.to_dict() if hasattr(job_obj, "to_dict") else job_obj
                ) or {}
                job_id = (
                    None
                    if not job_dict
                    else job_dict.get("id") or job_dict.get("job_id")
                )

                if not job_id:
                    logger.error(
                        f"No job ID returned from query job submission: {job_response}"
                    )
                else:
                    logger.debug(f"Polling org usage job {job_id}")
                    for attempt in range(max_polls):
                        time.sleep(poll_sleep)
                        entities = client.get(
                            "UsageApi",
                            "get_usage_aggregates_query_job",
                            job_id,
                        )
                        if entities:
                            for item in entities:
                                item_dict = (
                                    item.to_dict() if hasattr(item, "to_dict") else item
                                )
                                results.append(item_dict)
                            break
                    else:
                        logger.warning(
                            f"Org usage job {job_id} did not complete within {max_polls * poll_sleep}s"
                        )
            else:
                logger.error("Failed to submit org usage query job")

            event_counter = 0
            for item in results:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(item, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE_OPERATIONAL_USAGE_ORG,
                    )
                )
                event_counter += 1

            if event_counter > 0:
                logger.debug(f"Indexed {event_counter} org usage records")
                kvstore_checkpointer.update(checkpointer_key_name, now.timestamp())

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_OPERATIONAL_USAGE_ORG,
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

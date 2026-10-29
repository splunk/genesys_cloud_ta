"""Conversations Details input handler."""

import json
import logging
from datetime import datetime, timedelta, timezone

from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    SOURCETYPE_ANALYTICS_CONVERSATIONS_DETAILS,
)
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)
from genesys_cloud_ta.time_utils import exceed_range
from genesys_cloud_ta.validators import (
    validate_date,
)


def get_conversation_duration(start: datetime, end: datetime) -> int:
    """
    Calculate conversation duration.
    :param start: Conversation start datetime reference.
    :param end: Conversation end datetime reference.
    :return: Conversation duration in ms.
    """
    if end is None or start is None:
        return None
    duration = end - start
    return int(duration.total_seconds() * 1000)


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
                "conversations_details_checkpointer",
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
            # Setting a default start date of 7 days ago from now
            now = datetime.now(timezone.utc)
            fallback_start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            start_date = input_item.get("start_date")
            if start_date is not None:
                fallback_start = datetime.strptime(start_date, "%Y-%m-%d").strftime(  # noqa: DTZ007
                    "%Y-%m-%dT%H:%M:%SZ"
                )

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )
            checkpointer_key_name = normalized_input_name

            # Retrieve the last checkpoint
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
                "ConversationsApi",
                "post_analytics_conversations_details_query",
                "ConversationQuery",
                body,
            )
            # Careful: API call w/ paging! Needs conversion.
            data = client.convert_response(response, "conversations")

            if data:
                event_counter = 0
                for event in data:
                    # Adding conversation duration in milliseconds
                    duration = get_conversation_duration(
                        event["conversation_start"], event["conversation_end"]
                    )
                    event["conversation_duration"] = duration
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(event, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=SOURCETYPE_ANALYTICS_CONVERSATIONS_DETAILS,
                        )
                    )
                    event_counter += 1

                if event_counter > 0:
                    logger.debug(f"Indexed '{event_counter}' events")
                    logger.debug(f"Updating checkpointer to {end_time}")
                    kvstore_checkpointer.update(checkpointer_key_name, end_time)

                log.events_ingested(
                    logger,
                    input_name,
                    SOURCETYPE_ANALYTICS_CONVERSATIONS_DETAILS,
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

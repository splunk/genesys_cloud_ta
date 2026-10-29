"""Conversations Metrics input handler."""

import json
from datetime import datetime, timezone

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    CONVERSATIONS_METRICS,
    SOURCETYPE_ANALYTICS_CONVERSATIONS_METRICS,
)
from genesys_cloud_ta.time_utils import (
    get_interval_str,
    get_start_date,
)
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)
from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi


def validate_input(definition: smi.ValidationDefinition):
    """Validation function for the modular input (currently unused)."""
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            configure_logger(logger, session_key)

            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "conversations_metrics_checkpointer",
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
            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            # Setting a default start date of 7 days ago from now
            now = datetime.now(timezone.utc)
            checkpointer_key_name = normalized_input_name
            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)

            start_time = get_start_date(current_checkpoint, now)
            interval = get_interval_str(start_time, now)

            group_by = ["queueId"]

            media_types_raw = input_item.get("media_types", "")
            directions_raw = input_item.get("direction", "")
            media_types = media_types_raw.split("|") if media_types_raw else []
            directions = directions_raw.split("|") if directions_raw else []

            media_type_predicates = [
                {"dimension": "mediaType", "value": mt} for mt in media_types
            ]
            direction_predicates = [
                {"dimension": "direction", "value": d} for d in directions
            ]

            filter_block = {"type": "and", "clauses": []}
            if media_type_predicates:
                filter_block["clauses"].append(
                    {"type": "or", "predicates": media_type_predicates}
                )
            if direction_predicates:
                filter_block["clauses"].append(
                    {"type": "or", "predicates": direction_predicates}
                )

            body = {
                "interval": interval,
                "metrics": CONVERSATIONS_METRICS,
                "group_by": group_by,
                "filter": filter_block,
            }

            response = client.post(
                "ConversationsApi",
                "post_analytics_conversations_aggregates_query",
                "ConversationAggregationQuery",
                body,
            )
            to_process_data = client.convert_response(response)
            event_counter = 0
            for event in to_process_data:
                try:
                    for data_entry in event["data"]:
                        interval_start_time = (
                            datetime.strptime(
                                data_entry["interval"].split("/")[0],
                                "%Y-%m-%dT%H:%M:%S.%fZ",
                            )
                            .replace(tzinfo=timezone.utc)
                            .timestamp()
                            if event.get("data")
                            else round(start_time.timestamp(), 3)
                        )
                        for metric in data_entry["metrics"]:
                            metric["group"] = event["group"]
                            metric["interval"] = data_entry["interval"]
                            event_writer.write_event(
                                smi.Event(
                                    data=json.dumps(
                                        metric, ensure_ascii=False, default=str
                                    ),
                                    index=input_item.get("index"),
                                    sourcetype=SOURCETYPE_ANALYTICS_CONVERSATIONS_METRICS,
                                    time=interval_start_time,
                                )
                            )
                            event_counter += 1
                except RuntimeError as e:
                    logger.error(f"Failed to write event. Error: {e}")

            if event_counter > 0:
                logger.debug(f"Indexed '{event_counter}' events")
                new_checkpoint = now.timestamp()
                logger.debug(f"Updating checkpointer to {new_checkpoint}")
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_ANALYTICS_CONVERSATIONS_METRICS,
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

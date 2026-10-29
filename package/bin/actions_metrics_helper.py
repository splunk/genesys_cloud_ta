"""Actions Metrics input handler."""

import json
import logging
from datetime import datetime, timezone

from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    DEFAULT_ACTIONS_INTERVAL_SECONDS,
    SOURCETYPE_ANALYTICS_ACTIONS,
)
from genesys_cloud_ta.models import ActionModel
from genesys_cloud_ta.time_utils import (
    get_start_date,
    get_interval_str,
)
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)

def validate_input(definition: smi.ValidationDefinition):
    """Validation function for the modular input (currently unused)."""
    return

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        logger.info(f"Start processing input: {normalized_input_name}")
        try:
            session_key = inputs.metadata["session_key"]
            configure_logger(logger, session_key)

            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "actions_metrics_checkpointer", session_key, ADDON_NAME
            )

            proxy_config = get_proxy_configuration(logger, session_key)
            if proxy_config is None:
                continue

            log.modular_input_start(logger, normalized_input_name)

            account = input_item.get("account")
            logger.info(f"Retrieving credentials for account: {account}")

            account_region = get_account_property(session_key, account, "region")
            client_id = get_account_property(session_key, account, "client_id")
            client_secret = get_account_property(session_key, account, "client_secret")

            interval_seconds = int(
                input_item.get("interval", DEFAULT_ACTIONS_INTERVAL_SECONDS)
            )

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            checkpointer_key_name = normalized_input_name
            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)

            now = datetime.now(timezone.utc)
            start_time = get_start_date(current_checkpoint, now, interval_seconds)
            end_time = now

            interval = get_interval_str(start_time, end_time)

            body = {
                "interval": interval,
                "metrics": ["tTotalExecution"],
                "group_by": ["actionId"],
            }

            response = client.post(
                "AnalyticsApi",
                "post_analytics_actions_aggregates_query",
                "ActionAggregationQuery",
                body,
            )

            event_counter = 0
            to_process_data = client.convert_response(response)
            for event in to_process_data:
                try:
                    group_info = event.get("group", {}) or {}
                    a_model = ActionModel(event.get("data", []), group_info)
                    for data_entry in a_model.actions:
                        interval_range = data_entry.get("interval")
                        interval_start_time = (
                            data_entry.get_interval_start(interval_range)
                            if interval_range
                            else round(start_time.timestamp(), 3)
                        )
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(
                                    data_entry, ensure_ascii=False, default=str
                                ),
                                index=input_item.get("index"),
                                sourcetype=SOURCETYPE_ANALYTICS_ACTIONS,
                                time=interval_start_time,
                            )
                        )
                        event_counter += 1
                except Exception as e:  # noqa: BLE001
                    logger.error(f"Failed to write event: {e}")

            if event_counter > 0:
                new_checkpoint = end_time.timestamp()
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_ANALYTICS_ACTIONS,
                event_counter,
                input_item.get("index"),
                account=account,
            )
            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:  # noqa: BLE001
            log.log_exception(
                logger,
                e,
                "IngestionError",
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}",
            )

import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime, timezone
from genesyscloud_client import GenesysCloudClient

ADDON_NAME = "genesys_cloud_ta"

def logger_for_input(input_name: str) -> logging.Logger:
    """Create and return a logger for the specified input."""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def get_account_property(session_key: str, account_name: str, property_name: str):
    """Retrieve a specific property for a given Genesys Cloud account."""
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-genesys_cloud_ta_account",
    )
    account_conf_file = cfm.get_conf("genesys_cloud_ta_account")
    return account_conf_file.get(account_name).get(property_name)

def validate_input(definition: smi.ValidationDefinition):
    """Validation function for the modular input (currently unused)."""
    return

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    from datetime import datetime, timedelta, timezone

    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        logger.info(f"Start processing input: {normalized_input_name}")
        try:
            session_key = inputs.metadata["session_key"]

            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "actions_metrics_checkpointer", session_key, ADDON_NAME
            )

            log_level = conf_manager.get_log_level(
                logger=logger, session_key=session_key,
                app_name=ADDON_NAME, conf_name="genesys_cloud_ta_settings"
            )
            logger.setLevel(log_level)

            log.modular_input_start(logger, normalized_input_name)

            account = input_item.get("account")
            logger.info(f"Retrieving credentials for account: {account}")

            account_region = get_account_property(session_key, account, "region")
            client_id = get_account_property(session_key, account, "client_id")
            client_secret = get_account_property(session_key, account, "client_secret")

            client = GenesysCloudClient(logger, client_id, client_secret, account_region)

            checkpointer_key_name = normalized_input_name
            now = datetime.now(timezone.utc)

            # Read interval from input (default to 300 seconds if missing)
            interval_seconds = int(input_item.get("interval", "300"))

            # Load checkpoint or calculate backward if first run
            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)
            if current_checkpoint:
                start_time = datetime.fromtimestamp(current_checkpoint, tz=timezone.utc)
            else:
                # First run: go back `interval_seconds` from now
                start_time = now - timedelta(seconds=interval_seconds)

            end_time = now

            interval = f"{start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z/{end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"

            body = {
                "interval": interval,
                "metrics": ["tTotalExecution"],
                "group_by": ["actionId"],
            }

            response = client.post(
                "AnalyticsApi",
                "post_analytics_actions_aggregates_query",
                "ActionAggregationQuery",
                body
            )

            event_counter = 0
            res_dict = response.to_dict() or {}
            to_process_data = res_dict.get("results") or []

            for event in to_process_data:
                try:
                    group_info = event.get("group", {}) or {}
                    for data_entry in event.get("data", []):
                        interval_str = data_entry.get("interval")
                        interval_start_time = (
                            datetime.strptime(interval_str.split("/")[0], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
                            if interval_str else round(start_time.timestamp(), 3)
                        )

                        for metric in data_entry.get("metrics", []):
                            enriched_metric = {
                                "metric": metric.get("metric"),
                                "qualifier": metric.get("qualifier"),
                                "stats": metric.get("stats", {}),
                                "group": group_info,
                                "interval": interval_str
                            }

                            event_writer.write_event(
                                smi.Event(
                                    data=json.dumps(enriched_metric, ensure_ascii=False, default=str),
                                    index=input_item.get("index"),
                                    sourcetype="genesyscloud:analytics:actions:metrics",
                                    time=interval_start_time
                                )
                            )
                            event_counter += 1
                except Exception as e:
                    logger.error(f"Failed to write event: {e}")

            if event_counter > 0:
                new_checkpoint = end_time.timestamp()
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(logger, input_name, "genesyscloud:analytics:actions:metrics", event_counter, input_item.get("index"), account=account)
            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(logger, e, "IngestionError", msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}")

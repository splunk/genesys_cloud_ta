import json
import logging
from datetime import datetime

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from genesyscloud_client import GenesysCloudClient

ADDON_NAME = "genesys_cloud_ta"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def get_account_property(session_key: str, account_name: str, property_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-genesys_cloud_ta_account",
    )
    account_conf_file = cfm.get_conf("genesys_cloud_ta_account")
    return account_conf_file.get(account_name).get(property_name)

def validate_input(definition: smi.ValidationDefinition):
    return

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "chat_observations_checkpointer",
                session_key,
                ADDON_NAME,
            )
            
            # Setup logging and client
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="genesys_cloud_ta_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)
            
            # Get account credentials
            account_region = get_account_property(session_key, input_item.get("account"), "region")
            client_id = get_account_property(session_key, input_item.get("account"), "client_id")
            client_secret = get_account_property(session_key, input_item.get("account"), "client_secret")

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region
            )

            # Get checkpoint
            checkpointer_key_name = input_name.split("/")[-1]
            current_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or datetime(1970, 1, 1).timestamp()
            )

            # Query analytics API for chat metrics
            logger.debug("Fetching chat metrics")
            analytics_query = {
                "interval": "PT5M",  # 5 minute intervals
                "mediaTypes": ["CHAT"],
                "metrics": ["nOffered"],
                "groupBy": ["queueId"]
            }
            
            data = client.post(
                "AnalyticsApi",
                "post_analytics_conversations_aggregates_query",
                analytics_query
            )

            sourcetype = "genesyscloud:analytics:chat:metrics"
            metrics_written = 0
            
            # Process and write events
            for result in data.get("results", []):
                event_time = datetime.fromisoformat(result.get("interval").get("start"))
                event_time_epoch = event_time.timestamp()
                
                if event_time_epoch > current_checkpoint:
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(result, ensure_ascii=False),
                            time=event_time_epoch,
                            index=input_item.get("index"),
                            sourcetype=sourcetype,
                        )
                    )
                    metrics_written += 1

            # Update checkpoint if data was processed
            if metrics_written > 0:
                logger.debug("Updating checkpointer")
                new_checkpoint = datetime.utcnow().timestamp()
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                metrics_written,
                input_item.get("index"),
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
            
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "IngestionError", 
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}"
            )
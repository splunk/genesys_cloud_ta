import json
import logging
from datetime import datetime, timezone, timedelta

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
            account_region = get_account_property(session_key, input_item.get("account"), "region")
            client_id = get_account_property(session_key, input_item.get("account"), "client_id")
            client_secret = get_account_property(session_key, input_item.get("account"), "client_secret")

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region
            )
            logger.debug("[-] client created")
            checkpointer_key_name = input_name.split("/")[-1]
            # if we don't have any checkpoint, we default it to one hour ago
            # if the checkpoint is older than now, but newer than one hour ago, use it
            # otherwise, reset to one hour ago
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            one_hour_ago_timestamp = one_hour_ago.timestamp()
            
            stored_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)
            current_time = datetime.now(timezone.utc).timestamp()
            
            if stored_checkpoint and float(stored_checkpoint) <= current_time and float(stored_checkpoint) >= one_hour_ago_timestamp:
                current_checkpoint = stored_checkpoint
            else:
                current_checkpoint = one_hour_ago_timestamp
            logger.debug(f"[-] checkpoint: {current_checkpoint}" )
            start_time = datetime.fromtimestamp(current_checkpoint, tz=timezone.utc)
    
            now = datetime.now(timezone.utc)

            interval = f"{start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z/{now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"
            logger.debug(f"[-] interval: {interval}")
            metrics = ["nOffered"]
            filter = {
                "type": "and",
                "predicates": [
                    {
                        "dimension": "mediaType",
                        "operator": "matches",
                        "value": "message"
                    },
                    {
                        "dimension": "direction",
                        "operator": "matches",
                        "value": "inbound"
                    }
                ]
            }
            group_by = ["queueId"]


            body = {
                "interval": interval,
                "metrics" : metrics,
                "filter": filter,
                "group_by": group_by
            }

            response = client.post("ConversationsApi", "post_analytics_conversations_aggregates_query", "ConversationAggregationQuery", body)
            
            logger.debug(f"[-] response: {json.dumps(response, ensure_ascii=False, default=str)}")

            sourcetype = "genesyscloud:analytics:chat:metrics"
            metrics_written = 0
            
            if response.results is not None:
                # Process and write events
                for result_obj in response.results:
                    if now.timestamp() > current_checkpoint:
                        result = result_obj.to_dict()
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(result, ensure_ascii=False, default=str),
                                time=start_time.timestamp(),
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                            )
                        )
                        logger.debug(f"[-] event written: {json.dumps(result, ensure_ascii=False, default=str)}")
                        metrics_written += 1

            # Update checkpoint if data was processed
            if metrics_written > 0:
                logger.debug("[-] Updating checkpointer")
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
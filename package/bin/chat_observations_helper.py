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
            logger.debug("Genesys Cloud Client initialised")
            checkpointer_key_name = input_name.split("/")[-1]

             # Retrieve the last checkpoint or set it to 1970-01-01 if it doesn't exist
            current_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or datetime(1970, 1, 1).timestamp()
            )
            
            start_time = datetime.fromtimestamp(current_checkpoint, tz=timezone.utc)
            now = datetime.now(timezone.utc)

            # Define time interval for data retrieval
            interval = f"{start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z/{now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"
            metrics = [
                "nBlindTransferred", "nBotInteractions", "nCobrowseSessions", "nConnected",
                "nConsult", "nConsultTransferred", "nError", "nOffered", "nOutbound",
                "nOutboundAbandoned", "nOutboundAttempted", "nOutboundConnected", "nOverSla",
                "nStateTransitionError", "nTransferred", "oExternalMediaCount", "oMediaCount", "oMessageTurn", "oServiceLevel",
                "oServiceTarget", "tAbandon", "tAcd", "tActiveCallback", "tActiveCallbackComplete",
                "tAcw", "tAgentResponseTime", "tAlert", "tAnswered", "tBarging", "tCoaching",
                "tCoachingComplete", "tConnected", "tContacting", "tDialing", "tFirstConnect",
                "tFirstDial", "tFlowOut", "tHandle", "tHeld", "tHeldComplete", "tIvr",
                "tMonitoring", "tMonitoringComplete", "tNotResponding", "tPark", "tParkComplete",
                "tShortAbandon", "tTalk", "tTalkComplete", "tUserResponseTime", "tVoicemail",
                "tWait", "nOffered"
            ]

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
            
            logger.debug(f"Request body: {json.dumps(body, ensure_ascii=False, default=str)}")

            # Perform API request
            try:
                conv_model = client.post("ConversationsApi", "post_analytics_conversations_aggregates_query", "ConversationAggregationQuery", body)
                to_process_data = conv_model.to_dict().get("results", [])
            except Exception as e:
                logger.error(f"Error retrieving conversation metrics: {str(e)}")
                continue  # Skip processing if API call fails

            sourcetype = "genesyscloud:analytics:chat:metrics"
            metrics_written = 0
            
            # Ensure data exists before processing
            if to_process_data:
                for event in to_process_data:
                    try:
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(event, ensure_ascii=False, default=str),
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                                time=now.timestamp()
                            )
                        )
                        metrics_written += 1
                    except Exception as e:
                        logger.error(f"Failed to write event: {str(e)}")

                # Only update checkpoint if data was processed
                if metrics_written > 0:
                    try:
                        kvstore_checkpointer.update(checkpointer_key_name, now.timestamp())
                    except Exception as e:
                        logger.error(f"Failed to update checkpoint: {str(e)}")

                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    len(to_process_data),
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
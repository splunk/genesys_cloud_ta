import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
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
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]

            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "conversations_metrics_checkpointer",
                session_key,
                ADDON_NAME,
            )

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

            client = GenesysCloudClient(logger, client_id, client_secret, account_region)

            checkpointer_key_name = normalized_input_name
            # An 2025-10-14: Changed default start date to 5 minutes ago to reduce data volume on first run
            current_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or (datetime.now() - relativedelta(minutes=5)).timestamp()
            )

            start_time = datetime.fromtimestamp(current_checkpoint, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            interval = f"{start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z/{now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"

            metrics = [
                "nBlindTransferred", "nBotInteractions", "nCobrowseSessions", "nConnected",
                "nConsult", "nConsultTransferred", "nError", "nOffered", "nOutbound",
                "nOutboundAbandoned", "nOutboundAttempted", "nOutboundConnected", "nOverSla",
                "nStateTransitionError", "nTransferred", "oExternalMediaCount", "oMediaCount",
                "oMessageTurn", "oServiceLevel",
                "oServiceTarget", "tAbandon", "tAcd", "tActiveCallback", "tActiveCallbackComplete",
                "tAcw", "tAgentResponseTime", "tAlert", "tAnswered", "tBarging", "tCoaching",
                "tCoachingComplete", "tConnected", "tContacting", "tDialing", "tFirstConnect",
                "tFirstDial", "tFlowOut", "tHandle", "tHeld", "tHeldComplete", "tIvr",
                "tMonitoring", "tMonitoringComplete", "tNotResponding", "tPark", "tParkComplete",
                "tShortAbandon", "tTalk", "tTalkComplete", "tUserResponseTime", "tVoicemail",
                "tWait", "nOffered"
            ]
            group_by = ["queueId"]

            media_types_raw = input_item.get("media_types", "")
            directions_raw = input_item.get("direction", "")
            media_types = media_types_raw.split("|") if media_types_raw else []
            directions = directions_raw.split("|") if directions_raw else []

            media_type_predicates = [{"dimension": "mediaType", "value": mt} for mt in media_types]
            direction_predicates = [{"dimension": "direction", "value": d} for d in directions]

            filter_block = {"type": "and", "clauses": []}
            if media_type_predicates:
                filter_block["clauses"].append({"type": "or", "predicates": media_type_predicates})
            if direction_predicates:
                filter_block["clauses"].append({"type": "or", "predicates": direction_predicates})

            body = {
                "interval": interval,
                "metrics": metrics,
                "group_by": group_by,
                "filter": filter_block
            }

            sourcetype = "genesyscloud:analytics:flows:metrics"
            response = client.post(
                "ConversationsApi",
                "post_analytics_conversations_aggregates_query",
                "ConversationAggregationQuery",
                body
            )
            if response:
                event_counter = 0
                res_dict = response.to_dict() or {}
                to_process_data = res_dict.get("results") or []
                for event in to_process_data:
                    try:
                        for data_entry in event["data"]:
                            interval_start_time = (
                                datetime.strptime(data_entry["interval"].split("/")[0], "%Y-%m-%dT%H:%M:%S.%fZ").timestamp()
                                if event.get("data") else round(start_time.timestamp(), 3)
                            )
                            for metrics in data_entry["metrics"]:
                                metrics["group"] = event["group"]
                                metrics["interval"] = data_entry["interval"]
                                event_writer.write_event(
                                    smi.Event(
                                        data=json.dumps(metrics, ensure_ascii=False, default=str),
                                        index=input_item.get("index"),
                                        sourcetype=sourcetype,
                                        time=interval_start_time
                                    )
                                )
                                event_counter += 1
                    except Exception as e:
                        logger.error(f"Failed to write event. Error: {str(e)}")

                if event_counter > 0:
                    logger.debug(f"Indexed '{event_counter}' events")
                    new_checkpoint = now.timestamp()
                    logger.debug(f"Updating checkpointer to {new_checkpoint}")
                    kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    event_counter,
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

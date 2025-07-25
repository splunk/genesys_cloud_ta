import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime
from dateutil.relativedelta import relativedelta
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
    # Interval can be no greater than 7 days.
    start_date = definition.parameters.get("start_date")
    if start_date is not None:
        input_date = datetime.strptime(start_date, "%Y-%m-%d")
        threshold_date = datetime.now() - relativedelta(days=7)
        if input_date < threshold_date:
            raise Exception(f"Invalid start date {input_date}. Start date for data collection can be no greater than 7 days ago from now.")
    return

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "conversations_details_checkpointer",
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
            # Setting a default start date of 7 days ago from now
            now = datetime.now()
            fallback_start = (now - relativedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            start_date = input_item.get("start_date")
            if start_date is not None:
                fallback_start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%dT%H:%M:%SZ")

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region
            )
            checkpointer_key_name = input_name.split("/")[-1]

            # Retrieve the last checkpoint or set it to the fallback start date.
            start_time = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or fallback_start
            )
            end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            interval = f"{start_time}/{end_time}"

            body = {
                "interval": interval
            }
            logger.debug(f"Request body: {body}")

            response = client.post(
                "ConversationsApi",
                "post_analytics_conversations_details_query",
                "ConversationQuery",
                body
            )
            # Careful: API call w/ paging! Needs conversion.
            data = client.convert_response(response, "conversations")
            sourcetype = "genesyscloud:analytics:conversations:details"

            if data:
                event_counter = 0
                for event in data:
                    # Adding conversation duration in milliseconds
                    duration = get_conversation_duration(event["conversation_start"], event["conversation_end"])
                    event["conversation_duration"] = duration
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(event, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=sourcetype
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
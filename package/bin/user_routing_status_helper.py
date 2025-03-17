import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib import splunk_rest_client as rest_client
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime
from genesyscloud_client import GenesysCloudClient
from genesyscloud_models import UserModel


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
                "users_routing_status_checkpointer",
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

            client_id = get_account_property(session_key, input_item.get("account"), "client_id")
            client_secret = get_account_property(session_key, input_item.get("account"), "client_secret")
            account_region = get_account_property(session_key, input_item.get("account"), "region")

            # Initialize Genesys Cloud client
            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region
            )

            # Initialize checkpointing
            checkpointer_key_name = input_name.split("/")[-1]

            current_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or datetime(1970, 1, 1).timestamp()
            )

            # Getting user ids from API
            logger.info("Getting data from users endpoint")
            user_model = UserModel(
                client.get("UsersApi", "get_users")
            )

            #Getting user routing status
            sourcetype = "genesyscloud:users:users:routingstatus"
            rcounter = 0
            for uid in user_model.user_ids:
                response = client.get("UsersApi", "get_user_routingstatus", uid)

                if (response[0].start_time):
                    event_time_epoch = response[0].start_time.timestamp()

                    if event_time_epoch > current_checkpoint:
                        routing = response[0].to_dict()
                        routing["start_time"] = event_time_epoch
                        routing['user_id'] = user
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(routing, ensure_ascii=False, default=str),
                                time=event_time_epoch,
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                            )
                        )
                        rcounter += 1

            # Updating checkpoint if data was returned to avoid losing info
            if rcounter > 0:
                logger.debug("Updating checkpointer and leaving")
                new_checkpoint = datetime.utcnow().timestamp()
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                rcounter,
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

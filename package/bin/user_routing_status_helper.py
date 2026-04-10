import json
import logging

import import_declare_test
from solnlib import conf_manager, log
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

def get_account_proxy(logger, session_key: str):
    try:
        proxy_config = conf_manager.get_proxy_dict(
            logger=logger,
            session_key=session_key,
            app_name=ADDON_NAME,
            conf_name="genesys_cloud_ta_settings",
        )
    # Handle invalid port case
    except InvalidPortError as e:
        logger.error(f"Proxy configuration error: {e}")

    # Handle invalid hostname case
    except InvalidHostnameError as e:
        logger.error(f"Proxy configuration error: {e}")

    if not proxy_config or not proxy_config.get('proxy_enabled'):
        logger.info('Proxy is not enabled')
        return None

    url = proxy_config.get('proxy_url')
    port = proxy_config.get('proxy_port')
    user = proxy_config.get('proxy_username')
    password = proxy_config.get('proxy_password')

    if not all((user, password)):
        logger.info('Proxy has no credentials found')
        user, password = None, None

    proxy_type = proxy_config.get('proxy_type')
    proxy_type = proxy_type.lower() if proxy_type else 'http'

    proxy_url = f"{proxy_type}://{url}:{port}"

    return proxy_url, user, password

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "user_routing_status_checkpointer",
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

            proxy = get_account_proxy(logger=logger, session_key=session_key)
            if (proxy):
                proxy_url, proxy_username, proxy_password = proxy
            else:
                proxy_url, proxy_username, proxy_password = None, None, None
            # Initialize Genesys Cloud client
            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_url=proxy_url, proxy_username=proxy_username, proxy_password=proxy_password
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
                        routing['user_id'] = uid
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(routing, ensure_ascii=False, default=str),
                                time=event_time_epoch,
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                            )
                        )
                        rcounter += 1

            # Updating checkpoint if data was indexed to avoid losing info
            if rcounter > 0:
                logger.debug(f"Indexed '{rcounter}' events")
                new_checkpoint = datetime.utcnow().timestamp()
                logger.debug(f"Updating checkpointer to {new_checkpoint}")
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

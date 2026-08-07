import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from solnlib.conf_manager import InvalidHostnameError, InvalidPortError
from splunklib import modularinput as smi
from datetime import datetime, timezone, timedelta

from genesyscloud_client import GenesysCloudClient


ADDON_NAME = "genesys_cloud_ta"
SOURCETYPE = "genesyscloud:usage:events"


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
                "usage_events_checkpointer",
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
            try:
                proxy_config = conf_manager.get_proxy_dict(
                    logger=logger,
                    session_key=session_key,
                    app_name=ADDON_NAME,
                    conf_name="genesys_cloud_ta_settings",
                )
            except InvalidPortError as e:
                logger.error(f"Proxy configuration error: {e}")
                proxy_config = None
            except InvalidHostnameError as e:
                logger.error(f"Proxy configuration error: {e}")
                proxy_config = None
            log.modular_input_start(logger, normalized_input_name)

            client_id = get_account_property(session_key, input_item.get("account"), "client_id")
            client_secret = get_account_property(session_key, input_item.get("account"), "client_secret")
            account_region = get_account_property(session_key, input_item.get("account"), "region")

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            checkpointer_key_name = input_name.split("/")[-1]
            now = datetime.now(timezone.utc)
            last_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            )
            new_checkpoint = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            logger.info(f"Fetching usage events from {last_checkpoint} to {new_checkpoint}")

            body = {
                "interval": f"{last_checkpoint}/{new_checkpoint}",
            }
            response = client.post(
                "UsageApi",
                "post_usage_events_query",
                "ApiUsageQuery",
                body,
            )

            event_counter = 0
            if response is not None:
                results = client.convert_response(
                    [response] if not isinstance(response, list) else response,
                    "results"
                )
                for item in results:
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(item, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=SOURCETYPE,
                        )
                    )
                    event_counter += 1

            if event_counter > 0:
                logger.debug(f"Indexed {event_counter} usage event records")
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE,
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
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}",
            )

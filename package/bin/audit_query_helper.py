import json
import logging
import time

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime, timedelta, timezone, time as dt_time
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
    account_conf = cfm.get_conf("genesys_cloud_ta_account")
    return account_conf.get(account_name).get(property_name)


def validate_input(definition: smi.ValidationDefinition):
    pass


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)

        try:

            session_key = inputs.metadata["session_key"]

            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "audit_query_checkpointer",
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

            now = datetime.now(timezone.utc)
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()

            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name) or today_start

            start_time = datetime.fromtimestamp(current_checkpoint, tz=timezone.utc)
            interval = (
                f"{start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z/"
                f"{now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z"
            )

            body = {"interval": interval}

            response = client.post(
                "AuditApi",
                "post_audits_query",
                "AuditQueryRequest",
                body
            )

            if not response:
                raise Exception("No se recibió respuesta del POST de auditoría")

            transaction_id = response.id

            status = ""
            for i in range(10):
                state_response = client.get(
                    "AuditApi",
                    "get_audits_query_transaction_id",
                    transaction_id
                )

                if not state_response:
                    raise Exception("No se pudo obtener el estado del transaction_id")

                status = state_response[0].state

                if status == "Succeeded":
                    break
                time.sleep(2)

            if status != "Succeeded":
                raise Exception(f"Audit has not been completed: {status}")

            params = {
                "transaction_id": transaction_id,
                "page_size": 500
            }


            try:
                results = client.get(
                    "AuditApi",
                    "get_audits_query_transaction_id_results",
                    **params
                )
            except Exception as e:
                logger.error(
                    f"[GENESYS] Failed to retrieve audit transaction results.\n"
                    f"Endpoint: AuditApi.get_audits_query_transaction_id_results\n"
                    f"Params: {params}\n"
                    f"Error: {type(e).__name__} - {e}\n"       
                )

            for entity in results:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(entity.to_dict(), ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype="genesyscloud:audit:query",
                        time=entity.event_date.timestamp()
                    )
                )

            kvstore_checkpointer.update(checkpointer_key_name, now.timestamp())

        except Exception as e:
            logger.error(f"Error in input {normalized_input_name}: {str(e)}", exc_info=True)

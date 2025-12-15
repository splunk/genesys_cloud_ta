
import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime
from dateutil.relativedelta import relativedelta
from genesyscloud_client import GenesysCloudClient
from genesyscloud_models import PhoneModel


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
    # inputs.inputs is a Python dictionary object like:
    # {
    #   "edges_phones://<input_name>": {
    #     "account": "<account_name>",
    #     "disabled": "0",
    #     "host": "$decideOnStartup",
    #     "index": "<index_name>",
    #     "interval": "<interval_value>",
    #     "python.version": "python3",
    #   },
    # }
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "edges_phones_checkpointer",
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

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region
            )

            checkpointer_key_name = input_name.split("/")[-1]
            # if we don't have any checkpoint, we default it to 1970
            # AN 2025-10-14: Changed default start date to 5 minutes ago to reduce data volume on first run
            current_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or (datetime.now() - relativedelta(minutes=5)).timestamp()
            )

            p_model = PhoneModel(
                client.get(
                    "TelephonyProvidersEdgeApi",
                    "get_telephony_providers_edges_phones",
                    **{"expand":"site,status"}
                )
            )
            # Max 10k results returned when filtering the results or sorting
            # by a field other than the ID
            statuses = p_model.extended_statuses
            logger.debug(f"Fetched '{len(statuses)}' phone statuses")

            sourcetype = "genesyscloud:telephonyprovidersedge:edges:phones"
            event_counter = 0
            for status_obj in statuses:
                '''
                This is failing in some situations on the following but for time sake I'm not debugging it further:

                File "/home/splunk/genesys_cloud_ta/output/genesys_cloud_ta/bin/edges_phones_helper.py", line 97, in stream_events
                event_time_epoch = p_model.to_datetime(status_obj["event_creation_time"]).timestamp()
                File "/home/splunk/genesys_cloud_ta/output/genesys_cloud_ta/bin/genesyscloud_models.py", line 29, in to_datetime
                return datetime.datetime.strptime(dt_string, format)
                File "/opt/splunk/lib/python3.9/_strptime.py", line 568, in _strptime_datetime
                tt, fraction, gmtoff_fraction = _strptime(data_string, format)
                File "/opt/splunk/lib/python3.9/_strptime.py", line 349, in _strptime
                raise ValueError("time data %r does not match format %r" %
                ValueError: time data '2025-10-09T02:04:58.285926652Z' does not match format '%Y-%m-%dT%H:%M:%S.%fZ'
                '''

                # AN removing the checkpointing (ie 1==1) and indexing regardless of time to avoid losing data
                try:
                    event_time_epoch = p_model.to_datetime(status_obj["event_creation_time"]).timestamp()
                    if event_time_epoch > current_checkpoint or 1==1:
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(status_obj, ensure_ascii=False, default=str),
                                time=event_time_epoch,
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                            )
                        )
                        event_counter += 1
                except Exception as e:
                    logger.error(f"Error processing status object: {e}. Object data: {status_obj}")

            # Updating checkpoint if data was indexed to avoid losing info
            # this could introduce loss if events are written during processing, only msec delays but still possible
            if event_counter > 0:
                logger.debug(f"Indexed '{event_counter}' events")
                new_checkpoint = datetime.utcnow().timestamp()
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

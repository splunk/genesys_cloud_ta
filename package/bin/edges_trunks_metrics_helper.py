
import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib import splunk_rest_client as rest_client
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime
from genesyscloud_client import GenesysCloudClient
from genesyscloud_models import EdgeTrunkModel, to_string


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
    #   "edges_trunks_metrics://<input_name>": {
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
                "edges_trunks_metrics_checkpointer",
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
            # aws_region = input_item.get('region')

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region
            )

            checkpointer_key_name = input_name.split("/")[-1]
            # if we don't have any checkpoint, we default it to 1970
            current_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or datetime(1970, 1, 1).timestamp()
            )

            et_model = EdgeTrunkModel(client.get(
                "TelephonyProvidersEdgeApi", "get_telephony_providers_edges_trunks")
            )

            collection_names = ["gc_edges", "gc_trunks"]

            service = rest_client.SplunkRestClient(session_key, ADDON_NAME)
            for collection_name in collection_names:
                if collection_name not in service.kvstore:
                    # Create collection
                    logger.debug(f"Creating lookup '{collection_name}'")
                    service.kvstore.create(collection_name)

                # Update collection
                logger.debug(f"Saving data in lookup '{collection_name}'")
                collection = service.kvstore[collection_name]
                if collection_name.endswith("trunks"):
                    collection.data.batch_save(*et_model.trunks)
                    continue

                collection.data.batch_save(*et_model.edges)

            logger.debug("Indexing trunks metrics")
            data = client.get(
                "TelephonyProvidersEdgeApi",
                "get_telephony_providers_edges_trunks_metrics",
                ','.join(et_model.trunk_ids)
            )

            sourcetype = "genesyscloud:telephonyprovidersedge:trunks:metrics"
            for metric_obj in data:
                event_time_epoch = metric_obj.event_time.timestamp()
                metric = metric_obj.to_dict()
                metric["event_time"] = to_string(metric_obj.event_time)
                if event_time_epoch > current_checkpoint:
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(metric, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=sourcetype,
                        )
                    )

            # Updating checkpoint if data was returned to avoid losing info
            if data:
                logger.debug("Updating checkpointer and leaving")
                new_checkpoint = datetime.utcnow().timestamp()
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                len(data),
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

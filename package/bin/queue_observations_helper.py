import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib import splunk_rest_client as rest_client
from splunklib import modularinput as smi

from genesyscloud_client import GenesysCloudClient
from genesyscloud_models import QueueModel

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

            # Initializing lookup
            collection_name = "gc_queues"
            service = rest_client.SplunkRestClient(session_key, ADDON_NAME)
            if collection_name not in service.kvstore:
                # Create collection
                logger.debug(f"Creating lookup '{collection_name}'")
                service.kvstore.create(collection_name)

            # Getting data from API
            logger.info("Getting data from queues endpoint")
            queue_model = QueueModel(
                client.get(
                    "RoutingApi", "get_routing_queues"
                )
            )
            # Updating lookup
            logger.debug(f"Saving routing queues in lookup '{collection_name}'")
            collection = service.kvstore[collection_name]
            collection.data.batch_save(*queue_model.queues)

            # Getting metrics
            body = {
                "filter": {
                    "type": "or",
                    "clauses": [],
                    "predicates": [
                        {
                            "dimension": "queueId",
                            "operator": "matches",
                            "value": queue_id
                        } for queue_id in queue_model.queue_ids
                    ]
                },
                "metrics": [
                    "oActiveUsers", "oAlerting", "oInteracting",
                    "oMemberUsers", "oOffQueueUsers", "oOnQueueUsers",
                    "oUserPresences", "oUserRoutingStatuses", "oWaiting"
                ]
            }

            sourcetype = "genesyscloud:analytics:queues:observations"
            response = client.post(
                "RoutingApi",
                "post_analytics_queues_observations_query",
                "QueueObservationQuery",
                body
            )
            # Ensure data exists before processing
            if response:
                results = response.to_dict().get("results", [])
                event_counter = 0
                for item in results:
                    for data_entry in item["data"]:
                        data_entry["group"] = item["group"]
                        event_writer.write_event(
                            smi.Event(
                                # Index time not needed?
                                data=json.dumps(data_entry),
                                index=input_item.get("index"),
                                sourcetype=sourcetype
                            )
                        )
                        event_counter += 1

                # Checkpointing not needed?
                logger.debug(f"Indexed '{event_counter}' events")
                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    event_counter,
                    input_item.get("index"),
                    account = input_item.get("account")
                )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "IngestionError",
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}"
            )

import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi
from solnlib import splunk_rest_client as rest_client
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


def get_data_from_api(logger: logging.Logger, client, session_key):
    logger.info("Getting data from queues endpoint")
    def retrieve_routing_ids(logger: logging.Logger, client):
        queue_ids = []
        queue_lookup = []
        page_number = 1
        collection_name = "gc_queues"
        service = rest_client.SplunkRestClient(session_key, ADDON_NAME)
        if collection_name not in service.kvstore:
            # Create collection
            logger.debug(f"Creating lookup '{collection_name}'")
            service.kvstore.create(collection_name)
        try:
            while True:
                routing_model = client.get("RoutingApi", "get_routing_queues", page_size=500, page_number=page_number)
                for queue in routing_model:
                    queue_ids.append(queue.id)
                    queue_lookup.append(
                        {
                            "id": queue.id,
                            "name": queue.name
                        }
                    )
                if len(routing_model)<500:
                    break 
                else:
                    page_number += 1

        except Exception as e:
            logger.info(f"Error when calling RoutingApi->get_routing_queues: {e}")
        #Update queue lookup here
        logger.debug(f"[-] Saving data in lookup '{collection_name}'")
        collection = service.kvstore[collection_name]
        collection.data.batch_save(*queue_lookup)
        return queue_ids
    
    def get_metrics(logger: logging.Logger, client, queue_ids):
        body = {
            "filter": {
                "type": "or",
                "clauses": [],
                "predicates": [
                    {
                        "dimension": "queueId",
                        "operator": "matches",
                        "value": queue_id
                    } for queue_id in queue_ids
                ]
            },
            "metrics": ["oActiveUsers", "oAlerting", "oInteracting", "oMemberUsers", "oOffQueueUsers", "oOnQueueUsers", "oUserPresences", "oUserRoutingStatuses", "oWaiting"]  
        }

        try:
            queue_model = client.post("RoutingApi", "post_analytics_queues_observations_query", "QueueObservationQuery", body)
            to_process_data = queue_model.to_dict().get("results", [])
        except Exception as e:
            logger.info(f"Error when calling AnalyticsApi->post_analytics_queues_observations_query: {e}")
        return to_process_data

    queue_ids = retrieve_routing_ids(logger, client)
    logger.debug("[-] Retrieved queue list")
    results = get_metrics(logger, client, queue_ids)
    logger.debug("[-] Retrieved metric list")

    return results

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
            client = GenesysCloudClient(logger, client_id, client_secret, account_region)


            results = get_data_from_api(logger, client, session_key)
            sourcetype = "genesyscloud:analytics:queues:observations"
            logger.debug("[-] Indexing queue observations data")
            for item in results:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(item),
                        index=input_item.get("index"),
                        sourcetype=sourcetype
                    )
                )
                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    len(results), 
                    input_item.get("index"),
                    account = input_item.get("account")
                )
                log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "IngestionError", msg_before="Exception raised while ingesting data for demo_input: ")

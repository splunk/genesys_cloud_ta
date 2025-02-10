import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi
import PureCloudPlatformClientV2
import splunk.rest

ADDON_NAME = "genesys_cloud_ta"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def get_account_credentials(session_key: str, account_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-genesys_cloud_ta_account",
    )
    account_conf_file = cfm.get_conf("genesys_cloud_ta_account")
    return account_conf_file.get(account_name).get("client_id"), account_conf_file.get(account_name).get("client_secret")


def validate_input(definition: smi.ValidationDefinition):
    return

def retrieve_queues(logger: logging.Logger, routing_api):
    queues_list = []
    page_number = 1
    try:
        while True:
            queues = routing_api.get_routing_queues(page_size = 500, page_number = page_number)
            for queue in queues.entities:
                queues_list.append(
                    {
                        "id": queue.id,
                        "name": queue.name
                    }
                )
            if not queues.next_uri:
                break 
            else:
                page_number += 1

    except Exception as e:
        logging.info(f"Error when calling RoutingApi->get_routing_queues: {e}")
    return queues_list

def get_data_from_api(logger: logging.Logger, client_id: str, client_secret: str, opt_region: str):
    logger.info("Getting data from an external API")
    region = PureCloudPlatformClientV2.PureCloudRegionHosts[opt_region]
    PureCloudPlatformClientV2.configuration.host = region.get_api_host()
    apiclient = (
        PureCloudPlatformClientV2.api_client.ApiClient().get_client_credentials_token(
            client_id, client_secret
        )
    )
    routing_api = PureCloudPlatformClientV2.RoutingApi(apiclient)
    queue_list = retrieve_queues(logger, routing_api)
    logger.debug("[-] Retrieving queue list ended")
    return queue_ids

def stream_events(inputs: smi.InputDefinition, ew: smi.EventWriter):
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
            client_id, client_secret = get_account_credentials(session_key, input_item.get("account"))
            opt_region = input_item.get("region")
            queues_list = get_data_from_api(logger, client_id, client_secret, opt_region)

            # Convert queues_list to JSON format for insertion
            data = json.dumps(queues_list)
            logger.debug(f"[-] Data: {data}")

            # Define the lookup collection name. Replace 'queue_observations' with the name of your own lookup if needed.
            lookup_collection = "queues"

            # Construct the REST API URI for the KV Store collection batch_save endpoint.
            lookup_uri = f'/servicesNS/nobody/genesys_cloud_ta/storage/collections/data/{lookup_collection}/batch_save'

            logger.debug(f"[-] Lookup URI: {lookup_uri}")
            
            # Get the session key from the helper. This session key is necessary to authenticate the REST call.
            logger.debug(f"[-] Session Key: {session_key}")
            # Make the REST call
            response, content = splunk.rest.simpleRequest(lookup_uri,
                                                            method='POST',
                                                            sessionKey=session_key,
                                                            jsonargs=data)
            # Debug statements; you can remove these after testing.
            logger.debug(f"Queue lookup insertion response status: {response}")
            logger.debug(f"Queue lookup insertion response content: {content}")

        except Exception as e:
            logger.info(f"Error loading values into the lookup table '{lookup_collection}': {e}")
        
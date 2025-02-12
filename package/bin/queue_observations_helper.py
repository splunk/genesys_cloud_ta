import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi
import PureCloudPlatformClientV2

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


def get_data_from_api(logger: logging.Logger, client_id: str, client_secret: str, opt_region: str):
    logger.info("Getting data from an external API")
    def retrieve_routing_ids(logger: logging.Logger, routing_api):
        queue_ids = []
        page_number = 1
        try:
            while True:
                queues = routing_api.get_routing_queues(page_size = 500, page_number = page_number)
                for queue in queues.entities:
                    queue_ids.append(queue.id)
                if not queues.next_uri:
                    break 
                else:
                    page_number += 1

        except Exception as e:
            logger.info(f"Error when calling RoutingApi->get_routing_queues: {e}")
        return queue_ids
    
    def get_metrics(logger: logging.Logger, analytics_api, queue_ids):
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
        page_number = 1
        try:
            response = analytics_api.post_analytics_queues_observations_query(body)
        except Exception as e:
            logger.info(f"Error when calling AnalyticsApi->post_analytics_queues_observations_query: {e}")
        return response
    region = PureCloudPlatformClientV2.PureCloudRegionHosts[opt_region]
    PureCloudPlatformClientV2.configuration.host = region.get_api_host()
    apiclient = (
        PureCloudPlatformClientV2.api_client.ApiClient().get_client_credentials_token(
            client_id, client_secret
        )
    )
    routing_api = PureCloudPlatformClientV2.RoutingApi(apiclient)
    queue_ids = retrieve_routing_ids(logger, routing_api)
    logger.debug("Retrieved queue list")

    analytics_api = PureCloudPlatformClientV2.AnalyticsApi(apiclient)
    results = get_metrics(logger, analytics_api, queue_ids)
    logger.debug("Retrieved metric list")

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
            client_id, client_secret = get_account_credentials(session_key, input_item.get("account"))
            opt_region = input_item.get("region")

            results = get_data_from_api(logger, client_id, client_secret, opt_region)
            sourcetype = "queue_observations"
            for result in results.results:
                data = result.data
                group = result.group.get('queueId')
                data_dict = {}

                for item in range(0,len(data)):
                    data_dict[data[item].metric] = data[item].stats.count
                body = {"queueId": group, "data": data_dict}
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(body),
                        index=input_item.get("index"),
                        sourcetype=sourcetype
                    )
                )
                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    len(data), 
                    input_item.get("index"),
                    account = input_item.get("account")
                )
                log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ")

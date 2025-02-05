
import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi


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
    #return account_conf_file.get(account_name).get("api_key")
    return account_conf_file.get(account_name).get(property_name)


def get_data_from_api(logger: logging.Logger, api_key: str):
    logger.info("Getting data from an external API")
    dummy_data = [
        {
            "line1": "hello",
        },
        {
            "line2": "world",
        },
    ]
    return dummy_data

def get_routing_queues(helper, routing_api):
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
        helper.log_info(f"Error when calling RoutingApi->get_routing_queues: {e}")
    return queue_ids

def get_active_user(helper, analytics_api, queue_ids):
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
        helper.log_info(f"Error when calling AnalyticsApi->post_analytics_queues_observations_query: {e}")
    return response

def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    # inputs.inputs is a Python dictionary object like:
    # {
    #   "queue_observations://<input_name>": {
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
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="genesys_cloud_ta_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)
            #api_key = get_account_property(session_key, input_item.get("account"))
            region_arg = get_account_property(session_key, input_item.get("account"),"region")
            region = input_item.get('region')
            client_id = get_account_property(session_key, input_item.get("account"),"client_id")
            client_secret = get_account_property(session_key, input_item.get("account"),"client_secret")
            helper.log_info( "--- Hi I am here")
            helper.log_info(f"region_arg: {region_arg}")
            helper.log_info(f"region: {region}")
            helper.log_info(f"client_id: {client_id}")
            helper.log_info(f"client_secret: {client_secret}")
            #data = get_data_from_api(logger, api_key)


            # sourcetype = "dummy-data"
            # for line in data:
            #     event_writer.write_event(
            #         smi.Event(
            #             data=json.dumps(line, ensure_ascii=False, default=str),
            #             index=input_item.get("index"),
            #             sourcetype=sourcetype,
            #         )
            #     )
            # log.events_ingested(
            #     logger,
            #     input_name,
            #     sourcetype,
            #     len(data),
            #     input_item.get("index"),
            #     account=input_item.get("account"),
            # )
            # log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ")

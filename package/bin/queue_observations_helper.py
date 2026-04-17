import json
import logging

import import_declare_test
from solnlib import conf_manager, log
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
            proxy = get_account_proxy(logger=logger, session_key=session_key)
            if (proxy):
                proxy_url, proxy_username, proxy_password = proxy
            else:
                proxy_url, proxy_username, proxy_password = None, None, None
            # Initialize Genesys Cloud client
            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_url=proxy_url, proxy_username=proxy_username, proxy_password=proxy_password
            )

            # Getting data from API
            logger.info("Getting data from queues endpoint")
            queue_model = QueueModel(
                client.get(
                    "RoutingApi", "get_routing_queues"
                )
            )

            # Getting metrics
            # Max 200 query predicates according to error received
            results = []
            cnt = 0
            has_more = True
            while has_more:
                queue_ids, has_more = queue_model.get_queue_ids(cnt)
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
                    "metrics": [
                        "oActiveUsers", "oAlerting", "oInteracting",
                        "oMemberUsers", "oOffQueueUsers", "oOnQueueUsers",
                        "oUserPresences", "oUserRoutingStatuses", "oWaiting"
                    ]
                }
                response = client.post(
                    "RoutingApi",
                    "post_analytics_queues_observations_query",
                    "QueueObservationQuery",
                    body
                )
                # Ensure data exists before processing
                if response:
                    res_dict = response.to_dict() or {}
                    results.extend(res_dict.get("results", []) or [])
                cnt += 1
            logger.debug(f"Fetched '{len(results)}' queues observations")

            sourcetype = "genesyscloud:analytics:queues:observations"
            event_counter = 0
            for item in results:
                for data_entry in item["data"]:
                    data_entry["queue"] = queue_model.get_queue(item["group"]["queueId"])
                    event_writer.write_event(
                        smi.Event(
                            # Index time not needed?
                            data=json.dumps(data_entry, ensure_ascii=False, default=str),
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

import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi
from solnlib.modular_input import checkpointer
import PureCloudPlatformClientV2
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from genesyscloud_client import GenesysCloudClient

ADDON_NAME = "genesys_cloud_ta"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def get_account_property(session_key: str, account_name: str, property_name: str):
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            ADDON_NAME,
            realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-genesys_cloud_ta_account",
        )
        account_conf_file = cfm.get_conf("genesys_cloud_ta_account")
        return account_conf_file.get(account_name).get(property_name)
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve {property_name} for account {account_name}: {str(e)}")

def validate_input(definition: smi.ValidationDefinition):
    return

def get_data_from_api(logger: logging.Logger, current_checkpoint, last_checkpoint, client):
    logger.info("Getting data from users endpoint")
    def retrieve_users(logger: logging.Logger, client):
        user_data = []
        page_number = 1
        page_size = 500
        try:
            while True:
                user_info_model = client.get("UsersApi", "get_users", page_number=page_number, page_size=page_size)
                for user in user_info_model:
                    #Need to create a dictionary to write to user data lookup
                    user_data.append(user.id)
                if len(user_info_model)<page_size:
                    break 
                else:
                    page_number += 1
        except Exception as e:
            logger.info(f"Error when calling UserApi->get_users: {e}")
        #Write to user lookup here 
        return user_data

    def get_user_aggregates(logger: logging.Logger, current_checkpoint, last_checkpoint, user_data, client):
        batch_size = 100
        all_results = []

        interval = f"{current_checkpoint}/{last_checkpoint}"
        logger.debug(f"[-] finished interval: {interval}")
        user_batches = [user_data[i:i + batch_size] for i in range(0, len(user_data), batch_size)]
        for batch in user_batches:
            body = {
                "interval": interval,
                "granularity": "P1D",
                "groupBy": ["userId"],
                "metrics": ["tAgentRoutingStatus", "tOrganizationPresence", "tSystemPresence"],
                "filter": {
                    "type": "or",
                    "predicates": [
                        {
                            "dimension": "userId",
                            "operator": "matches",
                            "value": user_id
                        } for user_id in batch
                    ]
                }
            }

            try:
                user_model = client.post("UsersApi", "post_analytics_users_aggregates_query", "UserAggregationQuery", body)
                to_process_data = user_model.to_dict().get("results", [])
                all_results.append(to_process_data)
            except Exception as e:
                logger.info(f"Error when calling AnalyticsApi->post_analytics_users_aggregates_query: {e}")
        return all_results

    user_data = retrieve_users(logger, client)
    logger.debug("[-] Retrieving user information ended")
    results = get_user_aggregates(logger, current_checkpoint, last_checkpoint, user_data, client)
    logger.debug("[-] Retrieving user aggregates ended")
    return results

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "users_aggregates_checkpointer",
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
            client_id = get_account_property(session_key, input_item.get("account"), "client_id")
            client_secret = get_account_property(session_key, input_item.get("account"), "client_secret")
            account_region = get_account_property(session_key, input_item.get("account"), "region")
            # Initialize Genesys Cloud client
            client = GenesysCloudClient(logger, client_id, client_secret, account_region)

            checkpointer_key_name = input_name.split("/")[-1]
            logger.debug(f"[-] User aggregate checkpointer: {kvstore_checkpointer.get(checkpointer_key_name)}")
            # if we don't have any checkpoint, we default it to four years ago per API docs
            current = datetime.now()
            current_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or (current - relativedelta(years=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            last_checkpoint = current.strftime("%Y-%m-%dT%H:%M:%SZ")


            results = get_data_from_api(logger, current_checkpoint, last_checkpoint, client)
            sourcetype = "genesyscloud:analytics:users:aggregates"
            for item in results:
                for result in item:
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(result),
                            index=input_item.get("index"),
                            sourcetype=sourcetype
                        )
                    )
            logger.debug("[-] Updating checkpointer and leaving")
            kvstore_checkpointer.update(checkpointer_key_name, last_checkpoint)
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
import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from splunklib import modularinput as smi
from solnlib.modular_input import checkpointer
import PureCloudPlatformClientV2
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

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

def get_data_from_api(logger: logging.Logger, client_id: str, client_secret: str, opt_region: str, current_checkpoint: str, last_checkpoint: str):
    logger.info("Getting data from users endpoint")
    def retrieve_users(logger: logging.Logger, users_api):
        user_data = []
        page_number = 1
        try:
            while True:
                user_list = users_api.get_users(page_size = 500, page_number = page_number)
                for user in user_list.entities:
                    user_data.append(user.id)
                if not user_list.next_uri:
                    break 
                else:
                    page_number += 1
        except Exception as e:
            logger.info(f"Error when calling UserApi->get_users: {e}")
        return user_data

    def get_user_aggregates(logger: logging.Logger, analytics_api, user_data, current_checkpoint, last_checkpoint):
        batch_size = 100
        all_results = []

        interval = f"{current_checkpoint}/{last_checkpoint}"
        logger.debug(f"finished interval: {interval}")
        user_batches = [user_data[i:i + batch_size] for i in range(0, len(user_data), batch_size)]
        for batch in user_batches:
            # "2025-02-12T00:00:00Z/2025-02-13T00:05:00Z"
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
                response = analytics_api.post_analytics_users_aggregates_query(body)
                all_results.append(response)
            except Exception as e:
                logger.info(f"Error when calling AnalyticsApi->post_analytics_users_aggregates_query: {e}")
        return all_results

    region = PureCloudPlatformClientV2.PureCloudRegionHosts[opt_region]
    PureCloudPlatformClientV2.configuration.host = region.get_api_host()
    apiclient = (
        PureCloudPlatformClientV2.api_client.ApiClient().get_client_credentials_token(
            client_id, client_secret
        )
    )
    users_api = PureCloudPlatformClientV2.UsersApi(apiclient)
    user_data = retrieve_users(logger, users_api)
    logger.debug("Retrieving user information ended")

    analytics_api = PureCloudPlatformClientV2.AnalyticsApi(apiclient)
    results = get_user_aggregates(logger, analytics_api, user_data, current_checkpoint, last_checkpoint)
    logger.debug("Retrieving user aggregates ended")
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
            client_id, client_secret = get_account_credentials(session_key, input_item.get("account"))
            opt_region = input_item.get("region")
            opt_interval = input_item.get("interval")
            checkpointer_key_name = input_name.split("/")[-1]
            logger.debug(f"User aggregate checkpointer: {kvstore_checkpointer.get(checkpointer_key_name)}")
            # if we don't have any checkpoint, we default it to four years ago per API docs
            current = datetime.now()
            current_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or (current - relativedelta(years=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            last_checkpoint = current.strftime("%Y-%m-%dT%H:%M:%SZ")
            results = get_data_from_api(logger, client_id, client_secret, opt_region, current_checkpoint, last_checkpoint)
            sourcetype = "genesyscloud:analytics:users:aggregates"
            for item in results:
                for result in item.results:
                    data = result.data
                    group = result.group.get('userId')
                    data_dict = {}
                    for i in range(0,len(data)):
                        data_dict["interval"] = data[i].interval
                        data_dict["metric"] = data[i].metrics[0].metric
                        data_dict["qualifier"] = data[i].metrics[0].qualifier
                        data_dict["sum"] = data[i].metrics[0].stats.sum
                    body = {"userId": group, "data": data_dict}
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(body),
                            index=input_item.get("index"),
                            sourcetype=sourcetype
                        )
                    )
            logger.debug("Updating checkpointer and leaving")
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
            log.log_exception(logger, e, "my custom error type", msg_before="Exception raised while ingesting data for demo_input: ")
import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from genesyscloud_client import GenesysCloudClient
from genesyscloud_models import UserModel

'''
******************
WARNING: Dangerous Input
******************
This input will breach the fair usage limits if you have a lot of users
There is 1 API call for every user plus some overhead for pagination, 1 call per 25 users to build the initial list
The fair usage limit is system wide for the customner and if Splunk breaches it business critical systems may be affected.

Consider limiting this input to a few users using the filter option in the input configuration
call it infrequently, use A3S if available 
or event bridge instead if you need near real time data.
'''


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
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "user_aggregates_checkpointer",
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
            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region
            )

            # Initialize checkpointing
            checkpointer_key_name = input_name.split("/")[-1]
            now = datetime.now()
            # No checkpoint? Default it to four years ago per API docs
            # AN 2025-10-14: Changed default start date to 5 minutes ago to reduce data volume on first run
            last_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or (datetime.now() - relativedelta(minutes=5)).timestamp()
                #(now - relativedelta(years=4)).strftime("%Y-%m-%dT%H:%M:%SZ")
            )
            new_checkpoint = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Getting data from API
            logger.info("Getting data from users endpoint")
            user_model = UserModel(
                client.get("UsersApi", "get_users")
            )

            # Getting metrics
            interval = f"{last_checkpoint}/{new_checkpoint}"
            logger.info(f"Range interval: {interval}")

            # Max 100 userids supported according to specs (??)
            results = []
            cnt = 0
            has_more = True
            while has_more:
                user_ids, has_more = user_model.get_user_ids(cnt)
                body = {
                    "interval": interval,
                    "granularity": "P1D",
                    "groupBy": ["userId"],
                    "metrics": [
                        "tAgentRoutingStatus",
                        "tOrganizationPresence",
                        "tSystemPresence"
                    ],
                    "filter": {
                        "type": "or",
                        "predicates": [
                            {
                                "dimension": "userId",
                                "operator": "matches",
                                "value": uid
                            } for uid in user_ids
                        ]
                    }
                }
                data = client.post(
                    "UsersApi",
                    "post_analytics_users_aggregates_query",
                    "UserAggregationQuery",
                    body
                )
                if data:
                    res_dict = data.to_dict() or {}
                    results.extend(res_dict.get("results", []) or [])
                cnt+=1
            logger.debug(f"Fetched '{len(results)}' user aggregates")

            sourcetype = "genesyscloud:users:users:aggregates"
            event_counter = 0
            for item in results:
                for data_entry in item["data"]:
                    for metrics in data_entry["metrics"]:
                        metrics["user"] = user_model.get_user(item["group"]["userId"])
                        metrics["interval"] = data_entry["interval"]
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(metrics, ensure_ascii=False, default=str),
                                index=input_item.get("index"),
                                sourcetype=sourcetype
                            )
                        )
                        event_counter += 1

            # Updating checkpoint if data was indexed to avoid losing info
            if event_counter > 0:
                logger.debug(f"Indexed '{event_counter}' events")
                logger.debug(f"Updating checkpointer to {new_checkpoint}")
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

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

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


def get_data_from_api(logger: logging.Logger, client_id: str, client_secret: str, opt_region: str):
    logger.info("Getting data from users endpoint")
    def retrieve_users(logger: logging.Logger, users_api):
        user_data = []
        page_number = 1
        try:
            while True:
                user_list = users_api.get_users(page_size = 500, page_number = page_number)
                for user in user_list.entities:
                    user_data.append(
                        {
                            "id": user.id,
                            "name": user.name,
                            "division_id": user.division.id,
                            "division_name": user.division.name,
                            "chat": json.loads(user.chat.to_json()),
                            "email": user.email
                        }
                    )
                if not user_list.next_uri:
                    break 
                else:
                    page_number += 1
        except Exception as e:
            logger.info(f"Error when calling UserApi->get_users: {e}")
        return user_data

    region = PureCloudPlatformClientV2.PureCloudRegionHosts[opt_region]
    PureCloudPlatformClientV2.configuration.host = region.get_api_host()
    apiclient = (
        PureCloudPlatformClientV2.api_client.ApiClient().get_client_credentials_token(
            client_id, client_secret
        )
    )
    users_api = PureCloudPlatformClientV2.UsersApi(apiclient)
    user_data = retrieve_users(logger, users_api)
    logger.debug("Retrieving users ended")
    return user_data

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    
    # input_items = [{'count': len(inputs.inputs)}]

    # for input_name, input_item in inputs.inputs.items():
    #     input_item['name'] = input_name
    #     input_items.append(input_item)
    # event = smi.Event(
    #     data=json.dumps(input_items),
    #     sourcetype='user_lookup',
    # )
    # ew.write_event(event)


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
            data = json.dumps(results)
            logger.debug(f"[-] Data: {data}")
            lookup_collection = "gc_users"
            lookup_uri = f'/servicesNS/nobody/genesys_cloud_ta/storage/collections/data/{lookup_collection}/batch_save'
            response, content = splunk.rest.simpleRequest(lookup_uri,
                                                            method='POST',
                                                            sessionKey=session_key,
                                                            jsonargs=data)
            logger.debug(f"Finished inserting into {lookup_collection}")
        except Exception as e:
            logger.info(f"Error loading values into the user lookup table: {e}")
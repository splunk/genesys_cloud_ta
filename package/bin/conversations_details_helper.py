import json
import logging

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime, timezone, timedelta
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
        return None, None, None

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

def get_conversation_duration(start: datetime, end: datetime) -> int:
    """
    Calculate conversation duration.
    :param start: Conversation start datetime reference.
    :param end: Conversation end datetime reference.
    :return: Conversation duration in ms.
    """
    if end is None or start is None:
        return None
    duration = end - start
    return int(duration.total_seconds() * 1000)

def exceed_range(start: str, end: str, max_days: int = 31,
                  fmt: str = "%Y-%m-%dT%H:%M:%SZ") -> bool:
    """Verify interval range does not exceed threshold.
    :param start: Interval start string reference.
    :param end: Interval end string reference.
    :param max_days: Threshold in number of days.
    :param fmt: Datetime string format.
    :return: True if the range between start and end exceeds max_days.
    """
    start_dt = datetime.strptime(start, fmt)
    end_dt = datetime.strptime(end, fmt)

    if end_dt <= start_dt:
        raise Exception(f"Invalid start date: {start} cannot be later or equal to {end}")

    return (end_dt - start_dt) >= timedelta(days=max_days)

def validate_input(definition: smi.ValidationDefinition):
    start_date = definition.parameters.get("start_date")
    fmt_str = "%Y-%m-%d"
    if start_date is not None:
        if exceed_range(start_date, datetime.now().strftime(fmt_str), fmt=fmt_str):
            raise Exception(f"Invalid start date {start_date}. Start date for data collection cannot exceed 31 days from now.")
    return

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "conversations_details_checkpointer",
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
            account_region = get_account_property(session_key, input_item.get("account"), "region")
            client_id = get_account_property(session_key, input_item.get("account"), "client_id")
            client_secret = get_account_property(session_key, input_item.get("account"), "client_secret")
            # Setting a default start date of 7 days ago from now
            now = datetime.now(timezone.utc)
            fallback_start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            start_date = input_item.get("start_date")
            if start_date is not None:
                fallback_start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%dT%H:%M:%SZ")

            proxy_url, proxy_username, proxy_password = get_account_proxy(logger=logger, session_key=session_key)
            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_url=proxy_url, proxy_username=proxy_username, proxy_password=proxy_password
            )
            checkpointer_key_name = normalized_input_name

            # Retrieve the last checkpoint
            start_time = kvstore_checkpointer.get(checkpointer_key_name)
            end_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Evaluating the interval. It can be no greater than 31 days.
            # [400] BadRequest - You must specify a search interval as part of your query that does not exceed 31 days.
            if start_time is None or (start_time and exceed_range(start_time, end_time)):
                logger.info(f"Checkpoint not found or exceeds interval range of 31 days [{start_time}]. Using the configured start_date as fallback [{fallback_start}].")
                start_time = fallback_start
                if exceed_range(fallback_start, end_time):
                    # This case keeps the system running in case of too far away in time checkpoint.
                    reset_start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
                    logger.warn(f"Fallback start_date exceeds interval range of 31 days. Resetting it to {reset_start}.")
                    start_time = reset_start

            interval = f"{start_time}/{end_time}"

            body = {
                "interval": interval
            }
            logger.debug(f"Request body: {body}")

            response = client.post(
                "ConversationsApi",
                "post_analytics_conversations_details_query",
                "ConversationQuery",
                body
            )
            # Careful: API call w/ paging! Needs conversion.
            data = client.convert_response(response, "conversations")
            sourcetype = "genesyscloud:analytics:conversations:details"

            if data:
                event_counter = 0
                for event in data:
                    # Adding conversation duration in milliseconds
                    duration = get_conversation_duration(event["conversation_start"], event["conversation_end"])
                    event["conversation_duration"] = duration
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(event, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=sourcetype
                        )
                    )
                    event_counter += 1

                if event_counter > 0:
                    logger.debug(f"Indexed '{event_counter}' events")
                    logger.debug(f"Updating checkpointer to {end_time}")
                    kvstore_checkpointer.update(checkpointer_key_name, end_time)

                log.events_ingested(
                    logger,
                    input_name,
                    sourcetype,
                    event_counter,
                    input_item.get("index"),
                    account=input_item.get("account"),
                )

            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:
            log.log_exception(
                logger,
                e,
                "IngestionError",
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}"
            )
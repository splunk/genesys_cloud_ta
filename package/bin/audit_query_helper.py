import json
import logging
import time

import import_declare_test
from solnlib import conf_manager, log
from solnlib.conf_manager import InvalidHostnameError, InvalidPortError
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from datetime import datetime, timedelta, timezone
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
    account_conf = cfm.get_conf("genesys_cloud_ta_account")
    return account_conf.get(account_name).get(property_name)

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
                "audit_query_checkpointer",
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
            log.modular_input_start(logger, normalized_input_name)

            account_region = get_account_property(session_key, input_item.get("account"), "region")
            client_id = get_account_property(session_key, input_item.get("account"), "client_id")
            client_secret = get_account_property(session_key, input_item.get("account"), "client_secret")

            client = GenesysCloudClient(logger, client_id, client_secret, account_region, proxy_config)

            checkpointer_key_name = normalized_input_name

            # Setting a default start date of 7 days ago from now
            now = datetime.now(timezone.utc)
            fallback_start = (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
            start_date = input_item.get("start_date")
            if start_date is not None:
                fallback_start = datetime.strptime(start_date, "%Y-%m-%d").strftime("%Y-%m-%dT%H:%M:%SZ")

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

            body = { "interval": interval }
            logger.debug(f"Request body: {body}")

            response = client.post(
                "AuditApi",
                "post_audits_query",
                "AuditQueryRequest",
                body
            )
            if not response:
                raise Exception("No response was received from the audit POST request. Please verify the request parameters and try again.")

            transaction_id = response.id

            max_polls = int(input_item.get("max_poll_attempts", "10"))
            poll_sleep = int(input_item.get("poll_interval_seconds", "2"))

            status = ""
            for _ in range(max_polls):
                state_resp = client.get("AuditApi", "get_audits_query_transaction_id", transaction_id)
                if not state_resp:
                    raise Exception(f"Failed to get status for transaction {transaction_id}")
                status = state_resp[0].state
                # Allowed statuses:
                # https://github.com/MyPureCloud/platform-client-sdk-python/blob/master/build/PureCloudPlatformClientV2/models/audit_query_execution_status_response.py#L126
                if status in ("Succeeded", "Failed", "Cancelled"):
                    logger.debug(f"Audit complete with status '{status}'")
                    break
                time.sleep(poll_sleep)

            if status != "Succeeded":
                raise Exception(f"Audit did not complete successfully: {status}")

            params = {
                "transaction_id": transaction_id,
                "allow_redirect": True,
                "page_size": 500
            }

            results = client.get(
                "AuditApi",
                "get_audits_query_transaction_id_results",
                **params
            )
            event_counter = 0
            sourcetype="genesyscloud:operational:audits"

            for entity in results:
                if not isinstance(entity, dict):
                    value = entity.to_dict()
                    time_value = entity.event_date.timestamp()
                else:
                    # Retrieved via download URL file
                    value = entity
                    time_value = datetime.strptime(entity["eventTime"], "%Y-%m-%dT%H:%M:%SZ").timestamp()
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(value, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=sourcetype,
                        time=time_value
                    )
                )
                event_counter += 1

            # Update checkpoint with the interval end in ISO8601 to keep next run contiguous
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

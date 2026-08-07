import json
import logging
import time

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from solnlib.conf_manager import InvalidHostnameError, InvalidPortError
from splunklib import modularinput as smi
from datetime import datetime, timezone, timedelta

from genesyscloud_client import GenesysCloudClient


ADDON_NAME = "genesys_cloud_ta"
SOURCETYPE = "genesyscloud:usage:organization"

POLL_INTERVAL_SECONDS = 10
MAX_POLL_ATTEMPTS = 30


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
                "org_usage_checkpointer",
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
            except InvalidPortError as e:
                logger.error(f"Proxy configuration error: {e}")
                proxy_config = None
            except InvalidHostnameError as e:
                logger.error(f"Proxy configuration error: {e}")
                proxy_config = None
            log.modular_input_start(logger, normalized_input_name)

            client_id = get_account_property(session_key, input_item.get("account"), "client_id")
            client_secret = get_account_property(session_key, input_item.get("account"), "client_secret")
            account_region = get_account_property(session_key, input_item.get("account"), "region")

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            checkpointer_key_name = input_name.split("/")[-1]
            now = datetime.now(timezone.utc)
            last_checkpoint = (
                kvstore_checkpointer.get(checkpointer_key_name)
                or (now - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            )
            new_checkpoint = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            logger.info(f"Submitting org usage aggregates query job: {last_checkpoint} to {new_checkpoint}")

            body = {
                "interval": f"{last_checkpoint}/{new_checkpoint}",
                "granularity": "P1D",
            }

            job_response = client.post(
                "UsageApi",
                "post_usage_aggregates_query_jobs",
                "UsageAggregatesQueryRequest",
                body,
            )

            if job_response is None:
                logger.error("Failed to submit org usage query job")
                log.modular_input_end(logger, normalized_input_name)
                continue

            job_id = None
            if hasattr(job_response, "to_dict"):
                job_dict = job_response.to_dict()
                job_id = job_dict.get("id") or job_dict.get("job_id")
            elif isinstance(job_response, dict):
                job_id = job_response.get("id") or job_response.get("job_id")

            if not job_id:
                logger.error(f"No job ID returned from query job submission: {job_response}")
                log.modular_input_end(logger, normalized_input_name)
                continue

            logger.info(f"Polling org usage job {job_id}")
            results = []
            for attempt in range(MAX_POLL_ATTEMPTS):
                time.sleep(POLL_INTERVAL_SECONDS)
                status_response = client.get(
                    "UsageApi", "get_usage_aggregates_query_jobs_results",
                    job_id=job_id,
                )
                if status_response:
                    for item in status_response:
                        if hasattr(item, "to_dict"):
                            item_dict = item.to_dict()
                        else:
                            item_dict = item
                        if item_dict.get("data"):
                            results.extend(item_dict["data"])
                    break
            else:
                logger.warning(f"Org usage job {job_id} did not complete within {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s")

            event_counter = 0
            for item in results:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(item, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE,
                    )
                )
                event_counter += 1

            if event_counter > 0:
                logger.debug(f"Indexed {event_counter} org usage records")
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE,
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
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}",
            )

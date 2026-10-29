"""Usage Events input handler."""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    DEFAULT_MAX_POLL_ATTEMPTS,
    DEFAULT_POLL_INTERVAL_SECONDS,
    SOURCETYPE_OPERATIONAL_USAGE,
)
from genesys_cloud_ta.time_utils import (
    get_interval_str,
    get_start_date,
    to_epoch,
)
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)


def validate_input(definition: smi.ValidationDefinition):
    return


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            configure_logger(logger, session_key)
            kvstore_checkpointer = checkpointer.KVStoreCheckpointer(
                "usage_events_checkpointer",
                session_key,
                ADDON_NAME,
            )

            proxy_config = get_proxy_configuration(logger, session_key)
            if proxy_config is None:
                continue

            log.modular_input_start(logger, normalized_input_name)

            client_id = get_account_property(
                session_key, input_item.get("account"), "client_id"
            )
            client_secret = get_account_property(
                session_key, input_item.get("account"), "client_secret"
            )
            account_region = get_account_property(
                session_key, input_item.get("account"), "region"
            )

            max_polls = int(
                input_item.get("max_poll_attempts", DEFAULT_MAX_POLL_ATTEMPTS)
            )
            poll_sleep = int(
                input_item.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL_SECONDS)
            )

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            checkpointer_key_name = normalized_input_name
            now = datetime.now(timezone.utc)
            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)
            start_date = get_start_date(to_epoch(curr_checkpoint), now)

            body = {
                "interval": get_interval_str(start_date, now),
            }
            submit_response = client.post(
                "UsageApi",
                "post_usage_query",
                "ApiUsageOrganizationQuery",
                body,
            )

            logger.info("Fetching usage events.")

            results = []
            if submit_response:
                # client.post() always returns a list of API responses; the submit
                # query endpoint returns a single object, so take the first element.
                submit_obj = (
                    submit_response[0]
                    if isinstance(submit_response, list)
                    else submit_response
                )
                submit_dict = (
                    submit_obj.to_dict()
                    if hasattr(submit_obj, "to_dict")
                    else submit_obj
                ) or {}
                execution_id = (
                    None
                    if not submit_dict
                    else submit_dict.get("execution_id") or submit_dict.get("id")
                )

                if not execution_id:
                    logger.error(
                        f"No execution ID returned from usage events query: {submit_response}"
                    )
                else:
                    logger.info(f"Polling usage events execution {execution_id}")
                    for attempt in range(max_polls):
                        time.sleep(poll_sleep)
                        result_response = client.get(
                            "UsageApi",
                            "get_usage_query_execution_id_results",
                            execution_id,
                        )
                        if result_response:
                            results = client.convert_response(
                                result_response, "results"
                            )
                            if results:
                                break
                    else:
                        logger.warning(
                            f"Usage events execution {execution_id} did not complete within {max_polls * poll_sleep}s"
                        )
            else:
                logger.error("Failed to submit usage events query")

            event_counter = 0
            for item in results:
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(item, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE_OPERATIONAL_USAGE,
                    )
                )
                event_counter += 1

            if event_counter > 0:
                logger.debug(f"Indexed {event_counter} usage event records")
                kvstore_checkpointer.update(checkpointer_key_name, now.timestamp())

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_OPERATIONAL_USAGE,
                event_counter,
                input_item.get("index"),
                account=input_item.get("account"),
            )
            log.modular_input_end(logger, normalized_input_name)
        except Exception as e:  # noqa: BLE001
            log.log_exception(
                logger,
                e,
                "IngestionError",
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}",
            )

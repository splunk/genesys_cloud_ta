"""User Aggregates input handler."""

import json
from datetime import datetime, timezone

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    SOURCETYPE_USERS_USERS_AGGREGATES,
    USERS_AGGREGATES_METRICS,
)
from genesys_cloud_ta.models import UserModel
from genesys_cloud_ta.time_utils import (
    get_interval_str,
    get_start_date,
    to_epoch,
)
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)
from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi


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
                "user_aggregates_checkpointer",
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

            # Initialize Genesys Cloud client
            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            # Initialize checkpointing
            checkpointer_key_name = normalized_input_name
            now = datetime.now(timezone.utc)
            # No checkpoint? Default it to four years ago per API docs
            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)
            start_date = get_start_date(to_epoch(current_checkpoint), now, 1461 * 86400)

            # Getting data from API
            logger.info("Getting data from users endpoint")
            user_model = UserModel(client.get("UsersApi", "get_users"))

            # Getting metrics
            interval = (get_interval_str(start_date, now),)
            logger.debug(f"Range interval: {interval}")

            # Max 100 userids supported according to specs (??)
            results = []
            cnt = 0
            has_more = True
            while has_more:
                user_ids, has_more = user_model.get_user_ids(cnt)
                body = {
                    "interval": interval,
                    "granularity": "P1D",
                    "group_by": ["userId"],
                    "metrics": USERS_AGGREGATES_METRICS,
                    "filter": {
                        "type": "or",
                        "predicates": [
                            {"dimension": "userId", "operator": "matches", "value": uid}
                            for uid in user_ids
                        ],
                    },
                }
                data = client.post(
                    "UsersApi",
                    "post_analytics_users_aggregates_query",
                    "UserAggregationQuery",
                    body,
                )
                results.extend(client.convert_response(data))
                cnt += 1
            logger.debug(f"Fetched '{len(results)}' user aggregates")

            event_counter = 0
            for item in results:
                for data_entry in item["data"]:
                    for metrics in data_entry["metrics"]:
                        try:
                            metrics["user"] = user_model.get_user(
                                item["group"]["userId"]
                            )
                        except ValueError as ve:
                            logger.warning(
                                f"Could not get user information - {ve}. Skipping."
                            )
                            metrics["user"] = {}
                        metrics["interval"] = data_entry["interval"]
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(
                                    metrics, ensure_ascii=False, default=str
                                ),
                                index=input_item.get("index"),
                                sourcetype=SOURCETYPE_USERS_USERS_AGGREGATES,
                            )
                        )
                        event_counter += 1

            # Updating checkpoint if data was indexed to avoid losing info
            if event_counter > 0:
                logger.debug(f"Indexed '{event_counter}' events")
                new_checkpoint = now.timestamp()
                logger.debug(f"Updating checkpointer to {new_checkpoint}")
                kvstore_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_USERS_USERS_AGGREGATES,
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

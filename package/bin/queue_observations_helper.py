"""Queue Observations input handler."""

import json

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    QUEUE_OBSERVATIONS_METRICS,
    SOURCETYPE_ANALYTICS_QUEUE_OBSERVATIONS,
)
from genesys_cloud_ta.models import QueueModel
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)
from solnlib import log
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

            # Getting data from API
            logger.info("Getting data from queues endpoint")
            queue_model = QueueModel(client.get("RoutingApi", "get_routing_queues"))

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
                                "value": queue_id,
                            }
                            for queue_id in queue_ids
                        ],
                    },
                    "metrics": QUEUE_OBSERVATIONS_METRICS,
                }
                response = client.post(
                    "RoutingApi",
                    "post_analytics_queues_observations_query",
                    "QueueObservationQuery",
                    body,
                )
                results.extend(client.convert_response(response))
                cnt += 1
            logger.debug(f"Fetched '{len(results)}' queues observations")

            event_counter = 0
            for item in results:
                for data_entry in item["data"]:
                    try:
                        data_entry["queue"] = queue_model.get_queue(
                            item["group"]["queueId"]
                        )
                    except ValueError as ve:
                        logger.warning(
                            f"Could not get queue information - {ve}. Skipping."
                        )
                        data_entry["queue"] = {}
                    event_writer.write_event(
                        smi.Event(
                            # Index time not needed?
                            data=json.dumps(
                                data_entry, ensure_ascii=False, default=str
                            ),
                            index=input_item.get("index"),
                            sourcetype=SOURCETYPE_ANALYTICS_QUEUE_OBSERVATIONS,
                        )
                    )
                    event_counter += 1

            # Checkpointing not needed?
            logger.debug(f"Indexed '{event_counter}' events")
            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_ANALYTICS_QUEUE_OBSERVATIONS,
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

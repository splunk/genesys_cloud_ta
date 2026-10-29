"""Queues Inventory input handler."""

import json
import logging

from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    SOURCETYPE_INVENTORY_QUEUES,
)
from genesys_cloud_ta.models import QueueModel
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

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            logger.info("Fetching queues directory snapshot")
            queues = client.get("RoutingApi", "get_routing_queues")

            event_counter = 0
            for record in QueueModel(queues).get_directory_records():
                event_writer.write_event(
                    smi.Event(
                        data=json.dumps(record, ensure_ascii=False, default=str),
                        index=input_item.get("index"),
                        sourcetype=SOURCETYPE_INVENTORY_QUEUES,
                    )
                )
                event_counter += 1

            logger.debug(f"Indexed {event_counter} queue directory records")
            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_INVENTORY_QUEUES,
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

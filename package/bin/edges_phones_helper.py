"""Edges Phones input handler."""

import json
import logging
from datetime import datetime, timedelta, timezone

from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from genesys_cloud_ta.account import get_account_property
from genesys_cloud_ta.api.client import GenesysCloudClient
from genesys_cloud_ta.api.proxy import get_proxy_configuration
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    SOURCETYPE_TELEPHONYPE_PHONES,
)
from genesys_cloud_ta.models import PhoneModel
from genesys_cloud_ta.time_utils import get_start_date
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
                "edges_phones_checkpointer",
                session_key,
                ADDON_NAME,
            )

            proxy_config = get_proxy_configuration(logger, session_key)
            if proxy_config is None:
                continue

            log.modular_input_start(logger, normalized_input_name)

            account_region = get_account_property(
                session_key, input_item.get("account"), "region"
            )
            client_id = get_account_property(
                session_key, input_item.get("account"), "client_id"
            )
            client_secret = get_account_property(
                session_key, input_item.get("account"), "client_secret"
            )

            client = GenesysCloudClient(
                logger, client_id, client_secret, account_region, proxy_config
            )

            # Setting a default start date of 7 days ago from now
            now = datetime.now(timezone.utc)
            # fallback_start = (now - timedelta(days=7)).timestamp()
            checkpointer_key_name = normalized_input_name
            current_checkpoint = kvstore_checkpointer.get(checkpointer_key_name)
            start_date_epoch = get_start_date(current_checkpoint, now).timestamp()

            p_model = PhoneModel(
                client.get(
                    "TelephonyProvidersEdgeApi",
                    "get_telephony_providers_edges_phones",
                    expand="site,status",
                )
            )
            # Max 10k results returned when filtering the results or sorting
            # by a field other than the ID
            statuses = p_model.extended_statuses
            logger.debug(f"Fetched '{len(statuses)}' phone statuses")

            event_counter = 0
            for status_obj in statuses:
                event_time_epoch = p_model.to_datetime(
                    status_obj["event_creation_time"]
                ).timestamp()
                if event_time_epoch > start_date_epoch:
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(
                                status_obj, ensure_ascii=False, default=str
                            ),
                            time=event_time_epoch,
                            index=input_item.get("index"),
                            sourcetype=SOURCETYPE_TELEPHONYPE_PHONES,
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
                SOURCETYPE_TELEPHONYPE_PHONES,
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

"""Status Page Metrics input handler."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import requests
from genesys_cloud_ta.api.proxy import (
    ProxyHandler,
    get_proxy_configuration,
)
from genesys_cloud_ta.constants import (
    ADDON_NAME,
    SOURCETYPE_OPERATIONAL_SYSTEM,
    STATUS_PAGE_API_URL,
)
from genesys_cloud_ta.time_utils import get_start_date
from genesys_cloud_ta.utils import (
    configure_logger,
    logger_for_input,
)
from solnlib import log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi


def validate_input(definition: smi.ValidationDefinition):
    return


def fetch_status_page_data(logger: logging.Logger, proxy_url: str | None = None):
    """Fetch status data from the Genesys Cloud Status Page API"""
    try:
        # Get status summary instead of incidents
        proxies = None
        if proxy_url:
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            logger.info("Proxy enabled to fetch data.")
        summary_response = requests.get(
            f"{STATUS_PAGE_API_URL}/v2/summary.json", proxies=proxies
        )
        summary_response.raise_for_status()
        summary_data = summary_response.json()

        return summary_data
    except requests.RequestException as re:
        logger.error(f"Error fetching status page data: {re}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing response: {e}")
        return {}


def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            configure_logger(logger, session_key)
            status_page_checkpointer = checkpointer.KVStoreCheckpointer(
                "status_page_metrics_checkpointer",
                session_key,
                ADDON_NAME,
            )
            proxy_config = get_proxy_configuration(logger, session_key)
            if proxy_config is None:
                continue

            log.modular_input_start(logger, normalized_input_name)

            now = datetime.now(timezone.utc)
            checkpointer_key_name = normalized_input_name
            # If we don't have any checkpoint, we default it to 7 days ago
            current_checkpoint = status_page_checkpointer.get(checkpointer_key_name)
            start_date = get_start_date(current_checkpoint, now)

            logger.debug(f"Current status page checkpoint: {start_date}")

            proxy = ProxyHandler(logger, proxy_config)
            # Fetch data from Status Page API
            summary = fetch_status_page_data(logger, proxy_url=proxy.get_url_w_auth())

            # Process summary data
            events_count = 0

            page = summary.get("page", {})
            logger.debug(f"Summary data: {summary}")

            for component in summary.get("components", []):
                updated_at = component.get("updated_at", None)
                if updated_at:
                    component_updated_at = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    ).timestamp()
                    logger.debug(
                        f"Component updated at timestamp: {component_updated_at}"
                    )

                    # Only process if newer than our checkpoint
                    if component_updated_at > start_date.timestamp():
                        component["page"] = page
                        # Delete page_id field if it exists
                        if "page_id" in component:
                            logger.debug("Removing page_id field from component")
                            del component["page_id"]
                        logger.debug(f"Event data: {component}")

                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(
                                    component, ensure_ascii=False, default=str
                                ),
                                index=input_item.get("index"),
                                sourcetype=SOURCETYPE_OPERATIONAL_SYSTEM,
                                time=component_updated_at,
                            )
                        )
                        logger.debug("Status summary event written")
                        events_count += 1

            # Update checkpoint if data was processed
            new_checkpoint = now.timestamp()

            if events_count > 0:
                logger.debug(f"Updating status page checkpoint to {new_checkpoint}")
                status_page_checkpointer.update(checkpointer_key_name, new_checkpoint)

            log.events_ingested(
                logger,
                input_name,
                SOURCETYPE_OPERATIONAL_SYSTEM,
                events_count,
                input_item.get("index"),
            )

            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:  # noqa: BLE001
            log.log_exception(
                logger,
                e,
                "IngestionError",
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}",
            )

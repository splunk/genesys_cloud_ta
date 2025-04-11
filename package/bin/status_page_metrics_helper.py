import json
import logging
import requests
from datetime import datetime, timezone

from solnlib import conf_manager, log
from splunklib import modularinput as smi
from solnlib.modular_input import checkpointer


ADDON_NAME = "genesys_cloud_ta"
STATUS_PAGE_API_URL = "https://status.mypurecloud.com/api"

def logger_for_input(input_name: str) -> logging.Logger:
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def validate_input(definition: smi.ValidationDefinition):
    return

def get_account_property(session_key: str, account_name: str, property_name: str):
    cfm = conf_manager.ConfManager(
        session_key,
        ADDON_NAME,
        realm=f"__REST_CREDENTIAL__#{ADDON_NAME}#configs/conf-genesys_cloud_ta_account",
    )
    account_conf_file = cfm.get_conf("genesys_cloud_ta_account")
    return account_conf_file.get(account_name).get(property_name)

def fetch_status_page_data(logger: logging.Logger):
    """Fetch status data from the Genesys Cloud Status Page API"""
    try:
        # Get status summary instead of incidents
        summary_response = requests.get(f"{STATUS_PAGE_API_URL}/v2/summary.json")
        summary_response.raise_for_status()
        summary_data = summary_response.json()

        return summary_data
    except Exception as e:
        logger.error(f"Error fetching status page data: {str(e)}")
        return {}

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            status_page_checkpointer = checkpointer.KVStoreCheckpointer(
                "status_page_metrics_checkpointer",
                session_key,
                ADDON_NAME,
            )

            # Setup logging
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="genesys_cloud_ta_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)

            # Get checkpoints for incidents
            checkpointer_key_name = input_name.split("/")[-1]
            # If we don't have any checkpoint, we default it to 1970
            status_page_checkpoint = (
                status_page_checkpointer.get(checkpointer_key_name)
                or datetime(1970, 1, 1).timestamp()
            )

            logger.debug(f"Current status page checkpoint: {status_page_checkpoint}")

            # Fetch data from Status Page API
            summary = fetch_status_page_data(logger)

            # Process summary data
            sourcetype = "genesyscloud:operational:system"
            events_count = 0

            page = summary.get("page", {})
            logger.debug(f"Summary data: {summary}")

            for component in summary.get("components", []):
                component_updated_at = datetime.fromisoformat(component.get("updated_at").replace("Z", "+00:00")).timestamp()
                logger.debug(f"Component updated at timestamp: {component_updated_at}")

                # Only process if newer than our checkpoint
                if component_updated_at > status_page_checkpoint:

                    component["page"] = page
                    # Delete page_id field if it exists
                    if "page_id" in component:
                        logger.debug(f"Removing page_id field from component")
                        del component["page_id"]
                    logger.debug(f"Event data: {component}")

                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(component, ensure_ascii=False, default=str),
                            index=input_item.get("index"),
                            sourcetype=sourcetype,
                            time=component_updated_at
                        )
                    )
                    logger.debug(f"Status summary event written")
                    events_count += 1

            # Update checkpoint if data was processed
            current_time = datetime.now(timezone.utc).timestamp()

            if events_count > 0:
                logger.debug(f"Updating status page checkpoint to {current_time}")
                status_page_checkpointer.update(checkpointer_key_name, current_time)

            log.events_ingested(
                logger,
                input_name,
                sourcetype,
                events_count,
                input_item.get("index"),
                account=input_item.get("account")
            )

            log.modular_input_end(logger, normalized_input_name)

        except Exception as e:
            log.log_exception(
                logger,
                e,
                "IngestionError",
                msg_before=f"Exception raised while ingesting data for input: {normalized_input_name}"
            )
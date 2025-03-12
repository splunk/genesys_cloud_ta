import json
import logging
import requests
from datetime import datetime, timezone

import import_declare_test
from solnlib import conf_manager, log
from solnlib.modular_input import checkpointer
from splunklib import modularinput as smi

from genesyscloud_client import GenesysCloudClient

ADDON_NAME = "genesys_cloud_ta"
STATUS_PAGE_API_URL = "https://status.mypurecloud.com/api"

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

def fetch_status_page_data(logger: logging.Logger):
    """Fetch status data from the Genesys Cloud Status Page API"""
    try:
        # Get current incidents
        incidents_response = requests.get(f"{STATUS_PAGE_API_URL}/v2/incidents.json")
        incidents_response.raise_for_status()
        incidents_data = incidents_response.json()
        
        # Get component statuses
        components_response = requests.get(f"{STATUS_PAGE_API_URL}/v2/components.json")
        components_response.raise_for_status()
        components_data = components_response.json()
        
        return {
            "incidents": incidents_data.get("incidents", []),
            "components": components_data.get("components", [])
        }
    except Exception as e:
        logger.error(f"Error fetching status page data: {str(e)}")
        return {"incidents": [], "components": []}

def stream_events(inputs: smi.InputDefinition, event_writer: smi.EventWriter):
    for input_name, input_item in inputs.inputs.items():
        normalized_input_name = input_name.split("/")[-1]
        logger = logger_for_input(normalized_input_name)
        try:
            session_key = inputs.metadata["session_key"]
            
            # Setup logging
            log_level = conf_manager.get_log_level(
                logger=logger,
                session_key=session_key,
                app_name=ADDON_NAME,
                conf_name="genesys_cloud_ta_settings",
            )
            logger.setLevel(log_level)
            log.modular_input_start(logger, normalized_input_name)
            
            # Fetch data from Status Page API
            status_data = fetch_status_page_data(logger)
            
            # Process component status data
            now = datetime.now(timezone.utc)
            sourcetype = "genesyscloud:status:components"
            
            for component in status_data["components"]:
                try:
                    # Create event with component status
                    event_data = {
                        "id": component.get("id"),
                        "name": component.get("name"),
                        "status": component.get("status"),
                        "description": component.get("description", ""),
                        "group_id": component.get("group_id"),
                        "updated_at": component.get("updated_at"),
                        "position": component.get("position"),
                        "status_indicator": {
                            "up": component.get("status") == "operational",
                            "down": component.get("status") == "major_outage",
                            "warning": component.get("status") in ["partial_outage", "degraded_performance"]
                        }
                    }
                    
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(event_data, ensure_ascii=False),
                            index=input_item.get("index"),
                            sourcetype=sourcetype,
                            time=now.timestamp()
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to write component event: {str(e)}")
            
            # Process incident data
            sourcetype = "genesyscloud:status:incidents"
            for incident in status_data["incidents"]:
                try:
                    # Create event with incident details
                    event_data = {
                        "id": incident.get("id"),
                        "name": incident.get("name"),
                        "status": incident.get("status"),
                        "impact": incident.get("impact"),
                        "shortlink": incident.get("shortlink"),
                        "created_at": incident.get("created_at"),
                        "updated_at": incident.get("updated_at"),
                        "resolved_at": incident.get("resolved_at"),
                        "incident_updates": incident.get("incident_updates", []),
                        "components": incident.get("components", [])
                    }
                    
                    event_writer.write_event(
                        smi.Event(
                            data=json.dumps(event_data, ensure_ascii=False),
                            index=input_item.get("index"),
                            sourcetype=sourcetype,
                            time=now.timestamp()
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to write incident event: {str(e)}")
            
            log.events_ingested(
                logger,
                input_name,
                f"{sourcetype}",
                len(status_data["components"]) + len(status_data["incidents"]),
                input_item.get("index"),
                account=input_item.get("account")
            )
            
            log.modular_input_end(logger, normalized_input_name)
            
        except Exception as e:
            logger.error(f"Error in status_page_metrics input: {str(e)}")

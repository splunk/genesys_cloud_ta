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
            components_checkpointer = checkpointer.KVStoreCheckpointer(
                "components_metrics_checkpointer",
                session_key,
                ADDON_NAME,
            )
            incidents_checkpointer = checkpointer.KVStoreCheckpointer(
                "incidents_metrics_checkpointer",
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
            
            # Get checkpoints for components and incidents
            checkpointer_key_name = input_name.split("/")[-1]
            # If we don't have any checkpoint, we default it to 1970
            components_checkpoint = (
                components_checkpointer.get(checkpointer_key_name)
                or datetime(1970, 1, 1).timestamp()
            )
            incidents_checkpoint = (
                incidents_checkpointer.get(checkpointer_key_name)
                or datetime(1970, 1, 1).timestamp()
            )
            
            logger.debug(f"Current components checkpoint: {components_checkpoint}")
            logger.debug(f"Current incidents checkpoint: {incidents_checkpoint}")
            
            # Fetch data from Status Page API
            status_data = fetch_status_page_data(logger)
            
            # Process component status data
            sourcetype = "genesyscloud:status:components"
            components_count = 0
            
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

                    updated_at_str = component.get("updated_at")
                    updated_at_dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    updated_at_timestamp = updated_at_dt.timestamp()
                    
                    # Only process if newer than our checkpoint
                    if updated_at_timestamp > components_checkpoint:
                        logger.debug(f"Component event data: {event_data}")
                        
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(event_data, ensure_ascii=False),
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                                time=updated_at_timestamp
                            )
                        )
                        logger.debug(f"Component event written: {event_data}")
                        components_count += 1
                except Exception as e:
                    logger.error(f"Failed to write component event: {str(e)}")
            
            # Process incident data
            sourcetype = "genesyscloud:status:incidents"
            incidents_count = 0
            
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
                    
                    updated_at_str = incident.get("updated_at")
                    updated_at_dt = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    updated_at_timestamp = updated_at_dt.timestamp()
                    
                    # Only process if newer than our checkpoint
                    if updated_at_timestamp > incidents_checkpoint:
                        logger.debug(f"Incident event data: {event_data}")
                        
                        event_writer.write_event(
                            smi.Event(
                                data=json.dumps(event_data, ensure_ascii=False),
                                index=input_item.get("index"),
                                sourcetype=sourcetype,
                                time=updated_at_timestamp
                            )
                        )
                        logger.debug(f"Incident event written: {event_data}")
                        incidents_count += 1
                except Exception as e:
                    logger.error(f"Failed to write incident event: {str(e)}")
            
            # Update checkpoints if data was processed
            current_time = datetime.now(timezone.utc).timestamp()
            
            if status_data["components"]:
                logger.debug(f"Updating components checkpoint to {current_time}")
                components_checkpointer.update(checkpointer_key_name, current_time)
                
            if status_data["incidents"]:
                logger.debug(f"Updating incidents checkpoint to {current_time}")
                incidents_checkpointer.update(checkpointer_key_name, current_time)
            
            log.events_ingested(
                logger,
                input_name,
                "genesyscloud:status:components",
                components_count,
                input_item.get("index"),
                account=input_item.get("account")
            )
            
            log.events_ingested(
                logger,
                input_name,
                "genesyscloud:status:incidents",
                incidents_count,
                input_item.get("index"),
                account=input_item.get("account")
            )
            
            log.modular_input_end(logger, normalized_input_name)
            
        except Exception as e:
            logger.error(f"Error in status_page_metrics input: {str(e)}")

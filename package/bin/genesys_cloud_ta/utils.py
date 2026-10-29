import logging

from solnlib import conf_manager, log
from genesys_cloud_ta.constants import ADDON_NAME

def logger_for_input(input_name: str) -> logging.Logger:
    """Create and return a logger for the specified input."""
    return log.Logs().get_logger(f"{ADDON_NAME.lower()}_{input_name}")

def configure_logger(logger: logging.Logger, session_key: str) -> None:
    log_level = conf_manager.get_log_level(
        logger=logger,
        session_key=session_key,
        app_name=ADDON_NAME,
        conf_name="genesys_cloud_ta_settings",
    )
    logger.setLevel(log_level)

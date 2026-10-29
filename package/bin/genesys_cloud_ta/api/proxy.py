import logging

from solnlib.conf_manager import InvalidHostnameError, InvalidPortError
from solnlib.utils import is_true
from genesys_cloud_ta.constants import ADDON_NAME


def get_proxy_configuration(logger: logging.Logger, session_key: str) -> dict:
    try:
        return conf_manager.get_proxy_dict(
            logger=logger,
            session_key=session_key,
            app_name=ADDON_NAME,
            conf_name="genesys_cloud_ta_settings",
        )
    # Handle invalid port case
    except InvalidPortError as e:
        logger.error(f"Proxy configuration error: {e}")
        return None

    # Handle invalid hostname case
    except InvalidHostnameError as e:
        logger.error(f"Proxy configuration error: {e}")
        return None

class ProxyHandler:
    """Handle Proxy Configuration"""

    url: str = None
    url_auth: str = None
    username: str = None
    password: str = None

    def __init__(self, logger: logging.Logger, proxy_config: dict) -> None:
        if not proxy_config or not is_true(proxy_config.get("proxy_enabled")):
            logger.info("Proxy is not enabled")
            return

        host = proxy_config.get("proxy_url")
        port = proxy_config.get("proxy_port")
        proxy_type = proxy_config.get("proxy_type")
        proxy_type = proxy_type.lower() if proxy_type else "http"
        self.username = proxy_config.get("proxy_username", None)
        self.password = proxy_config.get("proxy_password", None)

        if not all((self.username, self.password)):
            logger.info("Proxy has no authentication")
        else:
            self.url_auth = (
                f"{proxy_type}://{self.username}:{self.password}@{host}:{port}"
            )

        self.url = f"{proxy_type}://{host}:{port}"

        logger.info(f"Using proxy: {self.url}")

    def get_url_w_auth(self) -> str:
        """
        To comply with requests library.
        """
        if not all((self.username, self.password)):
            return self.url
        else:
            return self.url_auth

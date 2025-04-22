import os
import sys
import pytest
import logging

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../package/bin")))
from genesyscloud_client import GenesysCloudClient
from PureCloudPlatformClientV2.api_client import ApiClient


LOGGER = logging.getLogger(__name__)
LOG_BUFFER = StringIO()
LOG_HANDLER = logging.StreamHandler(LOG_BUFFER)
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"
LOG_HANDLER.setFormatter(logging.Formatter(fmt=LOG_FORMAT))

LOGGER.addHandler(LOG_HANDLER)
LOG_HANDLER.setLevel(logging.DEBUG)

class GenesysCloudTATest():
    CLIENT_ID = None
    AWS_REGION = None
    CLIENT_SECRET = None

    gc_client = None
    logger = LOGGER

    @classmethod
    def setup_class(cls):
        cls.logger.info("Starting setup methods...")
        cls.logger.info("Test Begins.")
        cls.create_genesyscloud_client()

    @classmethod
    def teardown_class(cls):
        cls.delete_genesyscloud_accounts()

    def setup_method(cls, method):
        cls.logger.info(f"Setup method {method}")

    def teardown_method(cls, method):
        cls.logger.info(f"Tearing down method {method}")

    @classmethod
    def create_genesyscloud_client(cls):
        """
        Creates client using genesys_cloud_ta_accounts.conf
        """
        configs = cls.get_genesyscloud_accounts_configuration()
        cls.logger.info("Create client with config %s", configs)
        # Create client
        cls.gc_client = GenesysCloudClient(cls.logger, **configs)

    @classmethod
    def delete_genesyscloud_accounts(cls):
        """
        Deletes generated client
        """
        cls.logger.info("Delete client")
        cls.gc_client = None

    @classmethod
    def get_genesyscloud_accounts_configuration(cls):
        """
        Get the configuration for tenant from genesys_cloud_ta.conf
        :return configuration for creating client
        """

        configs = {
            "client_id": cls.CLIENT_ID,
            "client_secret": cls.CLIENT_SECRET,
            "aws_region": cls.AWS_REGION
        }
        cls.logger.info(f"{configs}")
        return configs

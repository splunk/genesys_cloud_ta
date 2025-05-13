import pytest
import logging

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import splunklib.client as client


LOGGER = logging.getLogger(__name__)
LOG_BUFFER = StringIO()
LOG_HANDLER = logging.StreamHandler(LOG_BUFFER)
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"
LOG_HANDLER.setFormatter(logging.Formatter(fmt=LOG_FORMAT))

LOGGER.addHandler(LOG_HANDLER)
LOG_HANDLER.setLevel(logging.DEBUG)

class BaseTATest():
    TA_APP_NAME = "genesys_cloud_ta"
    TA_APP_USER = "nobody"
    INDEX = "genesyscloud"
    CLIENT_ID = None
    AWS_REGION = None
    CLIENT_SECRET = None
    RETRY = 3
    LOOKUPS_MAPPING = {
        "edges_phones": "gc_phones",
        "queue_observations": "gc_queues"
    }

    logger = LOGGER
    splunk_url = None
    splunkd_port = None
    username = None
    password = None
    splunk_client = None

    @classmethod
    def setup_class(cls):
        cls.logger.info("Starting setup methods...")
        cls.logger.info("Test Begins.")
        cls.splunk_client = client.connect(
            host=cls.splunk_url,
            port=cls.splunkd_port,
            username=cls.username,
            password=cls.password,
            verify=False,
            sharing='app',
            app=cls.TA_APP_NAME)
        cls.create_genesyscloud_accounts()
        cls.logger.info("Creating index")
        cls.splunk_client.indexes.create(cls.INDEX)
        # Reloading the app to avoid issues
        cls.splunk_client.apps[cls.TA_APP_NAME].reload()


    @classmethod
    def teardown_class(cls):
        cls.delete_genesyscloud_accounts(f"{cls.TA_APP_NAME}_account")
        index = cls.splunk_client.indexes[cls.INDEX]
        # Clean index before deleting (removes all events)
        index.clean(timeout=300)
        index.delete()

        cls.splunk_client = None

    def setup_method(cls, method):
        cls.logger.info(f"Setup method {method.__name__}")
        cls.toggle_input(method.__name__.replace("test_input_", ""), 0)

    def teardown_method(cls, method):
        cls.logger.info(f"Tearing down method {method.__name__}")
        input_name = method.__name__.replace("test_input_", "")
        cls.toggle_input(input_name, 1)
        # Cleanup lookups
        lookup_name = cls.get_lookup_name(input_name)
        if lookup_name:
            kvstore_collection = cls.splunk_client.kvstore[lookup_name]
            cls.logger.info(f"Cleaning up data stored in lookup {lookup_name}")
            kvstore_collection.data.delete()
            # Manual cleanup from CLI
            # /opt/splunk/bin/splunk clean kvstore -app genesys_cloud_ta gc_phones
        # Clean up checkpointers
        try:
            checkpointer=f"{input_name}_checkpointer"
            kvstore_collection = cls.splunk_client.kvstore[checkpointer]
            cls.logger.info(f"Cleaning up checkpointer for input '{input_name}'")
            kvstore_collection.data.delete()
        except KeyError as err:
            # queue_observations does not use checkpointers
            cls.logger.warning(f"Skipping checkpointer cleanup: {checkpointer} not found - {err}")


    @classmethod
    def toggle_input(cls, input_name: str, new_state: int):
        """
        Enables/disables a specific input of the TA
        :param input_name: name of the input to be toggled
        :param new_state: state to be assigned to the input
        """
        input_obj = cls.splunk_client.inputs[input_name]
        cls.logger.info(f"Refreshing state of input {input_obj.content}")
        input_obj.refresh()
        current_state = input_obj.content.get('disabled')
        if int(current_state) != new_state:
            msg = "Disabling" if new_state == 1 else "Enabling"
            cls.logger.info(f"{msg} {input_name}")
            if new_state == 1:
                input_obj.disable()
            else:
                input_obj.enable()
            # Reload the app to avoid inconsistent states
            # cls.splunk_client.apps[cls.TA_APP_NAME].reload()

        # cls.logger.info(f"Check whether enabled? {inp.content}")
        # {'account': 'mock', 'disabled': '1', 'host': '$decideOnStartup', 'host_resolved': 'so1', 'index': 'genesyscloud', 'interval': '300', 'python.version': None}

    @classmethod
    def create_genesyscloud_accounts(cls):
        """
        Creates account using genesys_cloud_ta_accounts.conf
        """
        configs = cls.get_genesyscloud_accounts_configuration()
        cls.logger.info("Create account with config %s", configs)
        # Create account
        conf_filename = f"conf-{cls.TA_APP_NAME}_account"
        response = cls.splunk_client.post(
            f"configs/{conf_filename}", name="mock", **configs)
        cls.logger.info(f"Response {response}")

    @classmethod
    def delete_genesyscloud_accounts(cls, file_name=None):
        """
        Deletes generated accounts
        :param file_name: name of the config file storing account to delete"
        """
        cls.logger.info("Delete account")
        config_file = cls.splunk_client.confs[file_name]
        config_file.delete("mock")

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
        return configs

    @classmethod
    def get_lookup_name(cls, input_name: str) -> str:
        """
        Get the name of the lookup containing data for the given input
        :param input_name: name of the input storing data in the lookup
        """
        if input_name not in cls.LOOKUPS_MAPPING.keys():
            return None
        return cls.LOOKUPS_MAPPING.get(input_name, None)

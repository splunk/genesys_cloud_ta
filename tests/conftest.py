import pytest
import logging

logging.basicConfig(filename="conftest.log", level=logging.DEBUG)
LOGGER = logging.getLogger()

LOGGER.info("Root Conftest - Entering")


def pytest_addoption(parser):
    """
    Adds extra command line arguments to py.test
    """
    """
    This is a pytest hook to add options from the command line so that
    we can use it later.
    """
    gc_group = parser.getgroup("Genesys Cloud Options")
    gc_group.addoption(
        "--client-id",
        dest="client_id",
        help="the client id to access Genesys Cloud, defaults to myclientid",
        default="myclientid"
    )
    gc_group.addoption(
        "--client-secret",
        dest="client_secret",
        help="the password for client_id",
        default="myclientsecret, defaults to myclientsecret"
    )
    gc_group.addoption(
        "--aws-region",
        dest="aws_region",
        help="The AWS Region Genesys Cloud runs in, defaults to localhost:3004",
        default="localhost:3004"
    )
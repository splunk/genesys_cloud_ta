import logging
import pytest
import os
import sys
import base64
import datetime

from .BaseTATest import BaseTATest

logging.basicConfig(filename="conftest.log", level=logging.DEBUG)
LOGGER = logging.getLogger()

LOGGER.info("Conftest [modinput_functional] - Entering")


def pytest_addoption(parser):
    """
    Adds extra command line arguments to py.test
    """
    """
    This is a pytest hook to add options from the command line so that
    we can use it later.
    """
    splk_group = parser.getgroup("Splunk Options")
    splk_group.addoption(
        "--splunk-url",
        dest="splunk_url",
        help="The url of splunk instance, defaults to localhost",
        default="localhost",
    )
    splk_group.addoption(
        "--username",
        dest="username",
        help="Splunk username, defaults to admin",
        default="admin",
    )
    splk_group.addoption(
        "--password",
        dest="password",
        help="Splunk password, defaults to password",
        default="password",
    )
    splk_group.addoption(
        "--splunkd-port",
        dest="splunkd_port",
        help="Splunk Management port, defaults to 8089",
        default="8089",
    )


def pytest_configure(config):
    """
    Handles pytest configuration, runs before the session start.
    Initialize the parameters required test cases.
    """
    BaseTATest.username = config.getvalue("username")
    BaseTATest.password = config.getvalue("password")
    BaseTATest.splunk_url = config.getvalue("splunk_url")
    BaseTATest.splunkd_port = config.getvalue("splunkd_port")
    BaseTATest.CLIENT_ID = (
        config.getvalue("client_id")
        or base64.b64decode(os.environ["CLIENT_ID"]).decode().strip()
    )
    BaseTATest.CLIENT_SECRET = (
        config.getvalue("client_secret")
        or base64.b64decode(os.environ["CLIENT_SECRET"]).decode().strip()
    )
    BaseTATest.AWS_REGION = (
        config.getvalue("aws_region")
        or base64.b64decode(os.environ["AWS_REGION"]).decode().strip()
    )

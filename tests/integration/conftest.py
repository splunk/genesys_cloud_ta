import logging
import pytest
import os
import sys
import base64
import datetime

from random import randint
from .GenesysCloudTATest import GenesysCloudTATest

logging.basicConfig(filename="conftest.log", level=logging.DEBUG)
LOGGER = logging.getLogger()

LOGGER.info("IN CONFTEST")


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
        "--client_id",
        dest="client_id",
        help="the client id to access Genesys Cloud",
    )
    gc_group.addoption(
        "--client_secret",
        dest="client_secret",
        help="the password for client_id",
    )
    gc_group.addoption(
        "--aws_region",
        dest="aws_region",
        help="The AWS Region Genesys Cloud runs in",
    )

@pytest.fixture(scope="class")
def body_conversations():
    def _body_conversations(req_filter: dict = None):
        end_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')
        start_time = (datetime.datetime.utcnow() - datetime.timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S.%f')

        body = {
            "interval": f"{start_time[:-3]}Z/{end_time[:-3]}Z",
            "metrics": [
                "nBlindTransferred", "nBotInteractions", "nCobrowseSessions", "nConnected",
                "nConsult", "nConsultTransferred", "nError", "nOffered", "nOutbound",
                "nOutboundAbandoned", "nOutboundAttempted", "nOutboundConnected", "nOverSla",
                "nStateTransitionError", "nTransferred", "oExternalMediaCount", "oMediaCount", "oMessageTurn", "oServiceLevel",
                "oServiceTarget", "tAbandon", "tAcd", "tActiveCallback", "tActiveCallbackComplete",
                "tAcw", "tAgentResponseTime", "tAlert", "tAnswered", "tBarging", "tCoaching",
                "tCoachingComplete", "tConnected", "tContacting", "tDialing", "tFirstConnect",
                "tFirstDial", "tFlowOut", "tHandle", "tHeld", "tHeldComplete", "tIvr",
                "tMonitoring", "tMonitoringComplete", "tNotResponding", "tPark", "tParkComplete",
                "tShortAbandon", "tTalk", "tTalkComplete", "tUserResponseTime", "tVoicemail",
                "tWait", "nOffered"
            ],
            "group_by": ["queueId"]
        }
        if req_filter:
            body["filter"] = req_filter

        return body
    return _body_conversations

def pytest_configure(config):
    """
    Handles pytest configuration, runs before the session start.
    Initialize the parameters required test cases.
    """
    GenesysCloudTATest.CLIENT_ID = (
        config.getvalue("client_id")
        or base64.b64decode(os.environ["CLIENT_ID"]).decode().strip()
    )
    GenesysCloudTATest.CLIENT_SECRET = (
        config.getvalue("client_secret")
        or base64.b64decode(os.environ["CLIENT_SECRET"]).decode().strip()
    )
    GenesysCloudTATest.AWS_REGION = (
        config.getvalue("aws_region")
        or base64.b64decode(os.environ["AWS_REGION"]).decode().strip()
    )

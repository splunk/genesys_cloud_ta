import logging
import pytest
import os
import sys
import base64
import datetime

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
def body_basic():
    end_time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')
    start_time = (datetime.datetime.utcnow() - datetime.timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S.%f')
    return {
        "interval": f"{start_time[:-3]}Z/{end_time[:-3]}Z",
    }


@pytest.fixture(scope="class")
def body_conversations(request):
    def _body_conversations(req_metrics: bool, req_filter: dict):
        body = request.getfixturevalue("body_basic")

        if req_metrics:
            body_metrics = {
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
                body_metrics["filter"] = req_filter

            body.update(body_metrics)
        return body
    return _body_conversations

@pytest.fixture(scope="class")
def body_routing_queues():
    def _body_routing_queues(req_ids: list):
        if not req_ids:
            return {
                "filter": {
                    "type": "",
                    "clauses": [],
                    "predicates": []
                },
                "metrics": []
            }

        return {
            "filter": {
                "type": "or",
                "clauses": [],
                "predicates": [
                    {
                        "dimension": "queueId",
                        "operator": "matches",
                        "value": queue_id
                    } for queue_id in req_ids
                ]
            },
            "metrics": [
                "oActiveUsers", "oAlerting", "oInteracting",
                "oMemberUsers", "oOffQueueUsers", "oOnQueueUsers",
                "oUserPresences", "oUserRoutingStatuses", "oWaiting"
            ]
        }
    return _body_routing_queues


@pytest.fixture(scope="class")
def body_users(request):
    def _body_users(req_ids: list):
        body = request.getfixturevalue("body_basic")
        if not req_ids:
            body.update({
                "metrics": [],
                "group_by": [],
                "filter":  {
                    "type": "",
                    "clauses": [],
                    "predicates": []
                }
            })
            return body

        body_metrics = {
            "metrics": [
                "tAgentRoutingStatus",
                "tOrganizationPresence",
                "tSystemPresence"
            ],
            "group_by": ["userId"],
            "filter": {
                "type": "or",
                "predicates": [
                    {
                        "dimension": "userId",
                        "operator": "matches",
                        "value": uid
                    } for uid in req_ids
                ]
            }
        }
        body.update(body_metrics)
        return body

    return _body_users

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

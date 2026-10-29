"""Genesys Cloud Splunk Technical Add-on."""

ADDON_NAME = "genesys_cloud_ta"

"""Sourcetype constants for indexed events."""

SOURCETYPE_ANALYTICS_ACTIONS = "genesyscloud:analytics:actions:metrics"
SOURCETYPE_ANALYTICS_CONVERSATIONS_DETAILS = (
    "genesyscloud:analytics:conversations:details"
)
SOURCETYPE_ANALYTICS_CONVERSATIONS_METRICS = "genesyscloud:analytics:flows:metrics"
SOURCETYPE_ANALYTICS_QUEUE_OBSERVATIONS = "genesyscloud:analytics:queues:observations"
SOURCETYPE_INVENTORY_QUEUES = "genesyscloud:inventory:queues"
SOURCETYPE_INVENTORY_USERS = "genesyscloud:inventory:users"
SOURCETYPE_OPERATIONAL_AUDITS = "genesyscloud:operational:audits"
SOURCETYPE_OPERATIONAL_SYSTEM = "genesyscloud:operational:system"
SOURCETYPE_OPERATIONAL_USAGE = "genesyscloud:operational:events"
SOURCETYPE_OPERATIONAL_USAGE_CLIENTS = "genesyscloud:operational:usage:clients_api"
SOURCETYPE_OPERATIONAL_USAGE_ORG = "genesyscloud:operational:usage:api"
SOURCETYPE_TELEPHONYPE_EDGES_METRICS = (
    "genesyscloud:telephonyprovidersedge:edges:metrics"
)
SOURCETYPE_TELEPHONYPE_PHONES = "genesyscloud:telephonyprovidersedge:edges:phones"
SOURCETYPE_TELEPHONYPE_TRUNKS_METRICS = (
    "genesyscloud:telephonyprovidersedge:trunks:metrics"
)
SOURCETYPE_USERS_USERS_AGGREGATES = "genesyscloud:users:users:aggregates"
SOURCETYPE_USERS_ROUTING_STATUS = "genesyscloud:users:users:routingstatus"

"""Other parameters"""

MAX_PAGE_SIZE = 500

DEFAULT_HISTORICAL_DAYS = 7
DEFAULT_ACTIONS_INTERVAL_SECONDS = 300
DEFAULT_POLL_INTERVAL_SECONDS = 10
DEFAULT_MAX_POLL_ATTEMPTS = 30

STATUS_PAGE_API_URL = "https://status.mypurecloud.com/api"

# All statuses at:
# https://github.com/MyPureCloud/platform-client-sdk-python/blob/master/build/PureCloudPlatformClientV2/models/audit_query_execution_status_response.py#L126
AUDIT_QUERY_COMPLETED_STATUSES = frozenset({"Succeeded", "Failed", "Cancelled"})

CONVERSATIONS_METRICS = [
    "nBlindTransferred",
    "nBotInteractions",
    "nCobrowseSessions",
    "nConnected",
    "nConsult",
    "nConsultTransferred",
    "nError",
    "nOffered",
    "nOutbound",
    "nOutboundAbandoned",
    "nOutboundAttempted",
    "nOutboundConnected",
    "nOverSla",
    "nStateTransitionError",
    "nTransferred",
    "oExternalMediaCount",
    "oMediaCount",
    "oMessageTurn",
    "oServiceLevel",
    "oServiceTarget",
    "tWait",
    "tAbandon",
    "tAcd",
    "tActiveCallback",
    "tActiveCallbackComplete",
    "tAcw",
    "tAgentResponseTime",
    "tAlert",
    "tAnswered",
    "tBarging",
    "tCoaching",
    "tCoachingComplete",
    "tConnected",
    "tContacting",
    "tDialing",
    "tFirstConnect",
    "tFirstDial",
    "tFlowOut",
    "tHandle",
    "tHeld",
    "tHeldComplete",
    "tIvr",
    "tMonitoring",
    "tMonitoringComplete",
    "tNotResponding",
    "tPark",
    "tParkComplete",
    "tShortAbandon",
    "tTalk",
    "tTalkComplete",
    "tUserResponseTime",
    "tVoicemail",
]

QUEUE_OBSERVATIONS_METRICS = [
    "oActiveUsers",
    "oAlerting",
    "oInteracting",
    "oMemberUsers",
    "oOffQueueUsers",
    "oOnQueueUsers",
    "oUserPresences",
    "oUserRoutingStatuses",
    "oWaiting",
]

USERS_AGGREGATES_METRICS = [
    "tAgentRoutingStatus",
    "tOrganizationPresence",
    "tSystemPresence",
]

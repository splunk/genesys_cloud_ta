# Source types for the Genesys Cloud Add-On

The Genesys Cloud Add-on for Splunk provides the index-time and search-time knowledge for metrics, service status, and service message events in the following formats.

| Sourcetype | Description |
|:---:|---|
| `genesyscloud:telephonyprovidersedge:trunks:metrics` | All the metrics for trunks |
| `genesyscloud:telephonyprovidersedge:edges:metrics`  | All the metrics for edges  |
| `genesyscloud:telephonyprovidersedge:edges:phones`  | All phones statuses  |
| `genesyscloud:analytics:queues:observations` | All the metrics for queue observations |
| `genesyscloud:analytics:flows:metrics` | All the metrics for conversations |
| `genesyscloud:analytics:conversations:details` | All the score metrics for conversations, ex: MOS scores |
| `genesyscloud:users:users:aggregates` | All the metrics for user aggregates |
| `genesyscloud:users:users:routingstatus` | All the user routing status |
| `genesyscloud:operational:system` | All Genesys Cloud system services status retrieved via [Status Page API](https://metastatuspage.com/api#summary) |
| `genesyscloud:analytics:actions:metrics` | All the metrics for actions (aggregated by `actionId`) |
| `genesyscloud:operational:audits` | All the audit events |

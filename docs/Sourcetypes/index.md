# Source types for the Genesys Cloud Add-on

The Genesys Cloud Add-on for Splunk provides the index-time and search-time knowledge for metrics, service status, and service message events in the following formats.

| Sourcetype | Description | CIM Data Model / Dataset |
|:---:|---|---|
| `genesyscloud:telephonyprovidersedge:edges:metrics`  | All the metrics for edges  | [Performance](https://docs.splunk.com/Documentation/CIM/5.0.0/User/Performance) (All_Performance, CPU, Memory, Storage, Network, OS.Uptime) |
| `genesyscloud:telephonyprovidersedge:edges:phones`  | All phones statuses  | N/A |
| `genesyscloud:telephonyprovidersedge:trunks:metrics` | All the metrics for trunks | N/A |
| `genesyscloud:analytics:actions:metrics` | All the metrics for actions aggregated by `actionId` | N/A |
| `genesyscloud:analytics:conversations:details` | All the score metrics for conversations, e.g., MOS scores | N/A |
| `genesyscloud:analytics:flows:metrics` | All the metrics for conversations | N/A |
| `genesyscloud:analytics:queues:observations` | All the metrics for queue observations | N/A |
| `genesyscloud:users:users:aggregates` | All the metrics for user aggregates | N/A |
| `genesyscloud:users:users:routingstatus` | All the user routing statuses | N/A |
| `genesyscloud:operational:audits` | All the audit events | [Change](https://docs.splunk.com/Documentation/CIM/5.0.0/User/Change) (All_Changes, Account_Management), [Data_Access](https://docs.splunk.com/Documentation/CIM/5.0.0/User/DataAccess) |
| `genesyscloud:operational:system` | All Genesys Cloud system services status retrieved via [Status Page API](https://metastatuspage.com/api#summary) | N/A |
| `genesyscloud:operational:events` | All API usage event records | N/A |
| `genesyscloud:operational:usage:api` | All organization-level API usage aggregates | N/A |
| `genesyscloud:operational:usage:clients_api` | All OAuth client API usage aggregates | N/A |
| `genesyscloud:inventory:users` | All Genesys Cloud user records | N/A |
| `genesyscloud:inventory:queues` | All Genesys Cloud routing queue records | N/A |

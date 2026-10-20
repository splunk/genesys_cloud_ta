# Configure Operational inputs for the Genesys Cloud Add-on for Splunk

**Description:** Operational inputs enable collection of:

- System Services Status,
- Audit Query,
- Usage Operational Events,
- Organization API Usage,
- OAuth Client API Usage,
- Users Directory,
- Queues Directory.


## Pre-Requirements

Before you enable inputs, complete the previous steps in the configuration process:

- [Configure an integration application in Genesys Cloud for the Genesys Cloud Add-on for Splunk](../ConfigureGenesysCloud/index.md)
- [Configure an account in the Genesys Cloud Add-on for Splunk](../ConfigureAccount/index.md)

Configure your inputs on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder. You can configure inputs using Splunk Web (recommended) or using the configuration files.

## Configure inputs using Splunk Web

Configure your inputs using Splunk Web on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder.

1. In the Genesys Cloud Add-on for Splunk, click **Inputs > Create New Input > Operational**.
2. Select one of the available inputs among **System Services Status**, **Audit Query**, **Usage Operational Events**, **Organization API Usage**, **OAuth Client API Usage**, **Users Directory** and **Queues Directory**.
3. Enter the parameter values using information provided in the input parameter table below.
4. Click **Add**.
5. Verify that data is successfully arriving by running the following searches on your search head:

```bash
    sourcetype=genesyscloud:operational:*
```

If you do not see any events, check the [Troubleshooting](../Troubleshooting/index.md) section.

## Configure inputs in the configuration files

Configure your inputs using the configuration files on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder.

1. Create `$SPLUNK_HOME/etc/apps/genesys_cloud_ta/local/inputs.conf`.
2. Add the following stanza.

```
<!-- System Services Status -->
[status_page_metrics://<system_services_status_input_name>]
index = <value>
interval = <value>

<!-- Audit Query -->
[audit_query://<audit_query_input_name>]
account = <value>
index = <value>
interval = <value>
poll_interval_seconds = <value>
max_poll_attempts = <value>
start_date = <value>

<!-- Usage Operational Events -->
[usage_events://<usage_events_input_name>]
account = <value>
index = <value>
interval = <value>
poll_interval_seconds = <value>
max_poll_attempts = <value>

<!-- Organization API Usage -->
[org_usage://<org_usage_input_name>]
account = <value>
index = <value>
interval = <value>
poll_interval_seconds = <value>
max_poll_attempts = <value>

<!-- OAuth Client API Usage -->
[oauth_client_usage://<oauth_client_usage_input_name>]
account = <value>
index = <value>
interval = <value>
poll_interval_seconds = <value>
max_poll_attempts = <value>
oauth_client_id = <value>

<!-- Users Directory -->
[users_directory://<users_directory_input_name>]
account = <value>
index = <value>
interval = <value>

<!-- Queues Directory -->
[queues_directory://<queues_directory_input_name>]
account = <value>
index = <value>
interval = <value>

```

3. (Optional) Configure a custom `index`.
4. Restart your Splunk platform instance.
5. Verify that data is successfully arriving by running the following search on your search head:

```bash
    sourcetype=genesyscloud:operational:*
```

If you do not see any events, check the [Troubleshooting](../Troubleshooting/index.md) section.

## Input Parameters

Each attribute in the following table corresponds to a field in Splunk Web.

|Input name               |Corresponding field in Splunk Web | Description|
|-------------------------|----------------------------------|------------|
|`input_name`             |Input Name                        |A unique name for your input.|
|`account`                |Account Name                      |The Genesys Cloud account from which you want to gather data.|
|`index`                  |Index                             |The index in which the data should be stored. The default is <code>default</code>.|
|`interval`               |Interval (seconds)                |Rerun the input after the defined value, in seconds. The default value is <code>300</code> or  <code>86400</code> depending on the input.|
|`max_poll_attempts`      |Max Poll Attempts                 |Maximum number of status checks (polls) performed for an audit query or usage query transaction before giving up. The default value is <code>10</code> for Audit Query and <code>30</code> for the usage inputs, to be increased for long-running queries.|
|`poll_interval_seconds`  |Poll Interval (seconds)           |Seconds to wait between each status check of the audit query or usage query transaction. Lower values give quicker response but perform more API calls; higher values reduce rate-limit pressure. The default value is <code>2</code> for Audit Query and <code>10</code> for the usage inputs.|
|`start_date`            |Start Date                        |Date from which start collecting data. The default value is 7 days ago. Format: `YYYY-MM-DD`.
|`oauth_client_id`       |OAuth Client ID                   |Only for the OAuth Client API Usage input. The OAuth client ID to query usage for. If empty, queries usage for all clients.|

## Directory inputs: usage notes

The `users_directory` and `queues_directory` inputs ingest a **full snapshot** of the Genesys Cloud directory on every run (`GET /api/v2/users` and `GET /api/v2/routing/queues`). They are intended for scenarios where the directory data must be **indexed** (for example, historical lookup-table generation or compliance retention), rather than resolved on demand.

!!! note "On-demand alternative"
    If you only need to resolve user or queue IDs into human-readable names at search time (for dashboards), prefer the `| genesysusers` and `| genesysqueues` custom search commands shipped in the [Genesys Cloud App for Splunk](https://github.com/splunk/genesys_cloud_app_for_splunk). Those commands run on the Search Head and do not index data, which avoids the duplication described below.

### Deployment in a distributed environment

- Like every other input in this add-on, the directory inputs run on the Splunk platform instance where the add-on is installed, usually a **heavy forwarder**. They collect and forward data to the indexers; results are then searched from the **search head**.
- The data collected is directory/provisioning data (IDs, names, metadata), not time-series events. It changes infrequently, so a low collection frequency is recommended. The default `interval` for both inputs is `86400` (once per day), which is sufficient for most environments.

### Handling duplicates

- These inputs do **not** use checkpointing: each run re-indexes the **entire** directory as a fresh snapshot. This is intentional, so that deleted or renamed entities are reflected on each run, but it means the same `id` is indexed once per run and **duplicates accumulate over time**.
- When searching the indexed data, keep only the most recent snapshot per entity, for example:

```bash
    sourcetype=genesyscloud:directory:users
    | dedup id sortby -_time
```

- If the data is used purely for lookups and historical retention is not required, consider sending these inputs to a **dedicated index with a short retention policy** to keep the duplicate volume under control.

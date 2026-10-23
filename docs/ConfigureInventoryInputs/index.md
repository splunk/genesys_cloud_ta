# Configure Inventory inputs for the Genesys Cloud Add-on for Splunk

**Description:** Inventory inputs enable collection of:

- Users Directory,
- Queues Directory.


## Pre-Requirements

Before you enable inputs, complete the previous steps in the configuration process:

- [Configure an integration application in Genesys Cloud for the Genesys Cloud Add-on for Splunk](../ConfigureGenesysCloud/index.md)
- [Configure an account in the Genesys Cloud Add-on for Splunk](../ConfigureAccount/index.md)

Configure your inputs on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder. You can configure inputs using Splunk Web (recommended) or using the configuration files.

## Configure inputs using Splunk Web

Configure your inputs using Splunk Web on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder.

1. In the Genesys Cloud Add-on for Splunk, click **Inputs > Create New Input > Inventory**.
2. Select one of the available inputs among **Users Directory** and **Queues Directory**.
3. Enter the parameter values using information provided in the input parameter table below.
4. Click **Add**.
5. Verify that data is successfully arriving by running the following search on your search head:

```bash
    sourcetype=genesyscloud:inventory:*
```

If you do not see any events, check the [Troubleshooting](../Troubleshooting/index.md) section.

## Configure inputs in the configuration files

Configure your inputs using the configuration files on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder.

1. Create `$SPLUNK_HOME/etc/apps/genesys_cloud_ta/local/inputs.conf`.
2. Add the following stanza.

```
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
    sourcetype=genesyscloud:inventory:*
```

If you do not see any events, check the [Troubleshooting](../Troubleshooting/index.md) section.

## Input Parameters

Each attribute in the following table corresponds to a field in Splunk Web.

|Input name               |Corresponding field in Splunk Web | Description|
|-------------------------|----------------------------------|------------|
|`input_name`             |Input Name                        |A unique name for your input.|
|`account`                |Account Name                      |The Genesys Cloud account from which you want to gather data.|
|`index`                  |Index                             |The index in which the data should be stored. The default is <code>default</code>.|
|`interval`               |Interval (seconds)                |Rerun the input after the defined value, in seconds. The default value is <code>86400</code> (once per day), which is sufficient for most environments.|

## Usage notes

The `users_directory` and `queues_directory` inputs ingest a **full snapshot** of the Genesys Cloud directory on every run through `GET /api/v2/users` and `GET /api/v2/routing/queues`.

!!! warning
    **These inputs are intended for scenarios such as compliance retention where the directory data must be indexed**, rather than resolved on demand. Therefore, if you only need to resolve user or queue IDs into human-readable names at search time (for dashboards), we strongly recommend leveraging custom search commands instead.

### Deployment in a distributed environment

- Like every other input in this add-on, the inventory inputs run on the Splunk platform instance where the add-on is installed, usually a **heavy forwarder**. They collect and forward data to the indexers; results are then searched from the **search head**.
- The data collected is directory/provisioning data (IDs, names, metadata), not time-series events. It changes infrequently, so a low collection frequency is recommended. The default `interval` for both inputs is `86400` (once per day), which is sufficient for most environments.

### Handling duplicates

- These inputs do **not** use checkpointing: each run re-indexes the **entire** directory as a fresh snapshot. This is intentional, so that deleted or renamed entities are reflected on each run, but it means the same `id` is indexed once per run and **duplicates accumulate over time**.
- When searching the indexed data, keep only the most recent snapshot per entity, for example:

```bash
    sourcetype=genesyscloud:inventory:users
    | dedup id sortby -_time
```

- If the data is used purely for lookups and historical retention is not required, consider sending these inputs to a **dedicated index with a short retention policy** to keep the duplicate volume under control.

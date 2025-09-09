# Configure Operational inputs for the Genesys Cloud Add-on for Splunk

**Description:** Operational inputs enable collection of:

- System Services Status.
- Audit Query.


## Pre-Requirements

Before you enable inputs, complete the previous steps in the configuration process:

- [Configure an integration application in Genesys Cloud for the Genesys Cloud Add-on for Splunk](../ConfigureGenesysCloud/index.md)
- [Configure an account in the Genesys Cloud Add-on for Splunk](../ConfigureAccount/index.md)

Configure your inputs on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder. You can configure inputs using Splunk Web (recommended) or using the configuration files.

## Configure inputs using Splunk Web

Configure your inputs using Splunk Web on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder.

1. In the Genesys Cloud Add-on for Splunk, click **Inputs > Create New Input > Operational**.
2. Select one of the available inputs among **System Services Status** and **Audit Query**.
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
|`index`                  |Index                             |The index in which the data should be stored. The default is <code>default</code>.|
|`interval`               |Interval (seconds)                |Rerun the input after the defined value, in seconds. The default value is <code>300</code>.|
|`max_poll_attempts`      |Max Poll Attempts                 |Maximum number of status checks (polls) performed for an audit query transaction before giving up. The default value is <code>10</code>, to be increased for long-running queries.|
|`poll_interval_seconds`  |Poll Interval (seconds)           |Seconds to wait between each status check of the audit query `transaction_id`. Lower values give quicker response but perform more API calls; higher values reduce rate-limit pressure. The default value is <code>2</code>.|

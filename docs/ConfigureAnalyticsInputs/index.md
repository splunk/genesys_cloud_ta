# Configure Analytics inputs for the Genesys Cloud Add-on for Splunk

**Description:** Analytics inputs enable collection of:

- Queue Observations,
- Chat Observations,
- User Aggregates,
- Conversations Metrics,
- Conversations Details.

Collection of queue and user details is enabled into [lookups](../Lookups/index.md).

## Pre-Requirements

Before you enable inputs, complete the previous steps in the configuration process:

- [Configure an integration application in Genesys Cloud for the Genesys Cloud Add-on for Splunk](../ConfigureGenesysCloud/index.md)
- [Configure an account in the Genesys Cloud Add-on for Splunk](../ConfigureAccount/index.md)

Configure your inputs on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder. You can configure inputs using Splunk Web (recommended) or using the configuration files.

## Configure inputs using Splunk Web

Configure your inputs using Splunk Web on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder.

1. In the Genesys Cloud Add-on for Splunk, click **Inputs > Create New Input > Analytics**.
2. Select one of the available inputs among **Queue Observations**, **Chat Observations**, **User Aggregates**, **Conversations Metrics** and **Conversations Details**.
3. Enter the parameter values using information provided in the input parameter table below.
4. Click **Add**.
5. Verify that data is successfully arriving by running the following searches on your search head:

```bash
    sourcetype=genesyscloud:analytics:*
```

If you do not see any events, check the **Troubleshooting** tab on your data collection node to verify that your accounts, forwarders, and inputs are all configured successfully.

## Configure inputs in the configuration files

Configure your inputs using the configuration files on the Splunk platform instance responsible for collecting data for this add-on, usually a heavy forwarder.

1. Create `$SPLUNK_HOME/etc/apps/genesys_cloud_ta/local/inputs.conf`.
2. Add the following stanza.

```
<!-- Queue Observations -->
[queue_observations://<queue_observations_input_name>]
account = <value>
index = <value>
interval = <value>

<!-- Chat Observations -->
[chat_observations://<chat_observations_input_name>]
account = <value>
index = <value>
interval = <value>

<!-- User Aggregates -->
[user_aggregates://<user_aggregates_input_name>]
account = <value>
index = <value>
interval = <value>

<!-- Conversations Metrics -->
[conversations_metrics://<conversations_metrics_input_name>]
account = <value>
index = <value>
interval = <value>

<!-- Conversations Details -->
[conversations_details://<conversations_details_input_name>]
account = <value>
index = <value>
interval = <value>
```

3. (Optional) Configure a custom `index`.
4. Restart your Splunk platform instance.
5. Verify that data is successfully arriving by running the following search on your search head:

```bash
    sourcetype=genesyscloud:analytics:*
```

If you do not see any events, check the **Troubleshooting** tab on your data collection node to verify that your accounts, forwarders, and inputs are all configured successfully.

## Input Parameters

Each attribute in the following table corresponds to a field in Splunk Web.

|Input name               |Corresponding field in Splunk Web | Description|
|-------------------------|----------------------------------|------------|
|`input_name`             |Input Name                        |A unique name for your input.|
|`account`                |Account Name                      |The Genesys Cloud account from which you want to gather data.|
|`index`                  |Index                             |The index in which the data should be stored. The default is <code>default</code>.|
|`interval`               |Interval (seconds)                |Rerun the input after the defined value, in seconds. The default value is <code>300</code>.|

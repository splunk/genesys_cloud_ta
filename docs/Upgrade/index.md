# Upgrade the Genesys Cloud Add-on for Splunk

Before releasing 1.0.0 the Genesys Cloud Add-on for Splunk is still in the development phase, therefore version 1.0.0 is not backward compatible and will result in complete data duplication due to major checkpoint and events ingestion changes.

[Release Notes](https://github.com/splunk/genesys_cloud_ta/releases)

## Upgrade to version 0.2.x

1. Disable all inputs.
2. Download the latest version of Genesys Cloud Add-on for Splunk from its [repository](https://github.com/splunk/genesys_cloud_ta/releases).
3. [Install](../Install/index.md) the Genesys Cloud Add-on for Splunk across your deployment.
    > If installing via Splunk Web, select the `Upgrade app` checkbox.
4. Enable the inputs.


Data that was previously stored into KV Store lookups is now added into indexed events. More fields will be available at search time as a consequence.


## Upgrade to version 0.1.0

1. Disable and delete all inputs.
2. Delete created account(s) under _Configuration_.
3. Download the latest version of Genesys Cloud Add-on for Splunk from its [repository](https://github.com/splunk/genesys_cloud_ta/releases).
4. [Install](../Install/index.md) the Genesys Cloud Add-on for Splunk across your deployment.
5. [Configure](../ConfigureAccount/index.md) the Add-on.

The analytic input **Chat Observations** was removed. Alternatively, users can now [configure an equivalent analytic **Conversations Metrics** input](../ConfigureAnalyticsInputs/index.md) with:

* `direction = inbound`
* `media_types = message`

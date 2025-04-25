# Upgrade the Genesys Cloud Add-on for Splunk

Before releasing 1.0.0 the Genesys Cloud Add-on for Splunk is still in the development phase, therefore version 1.0.0 is not backward compatible and will result in complete data duplication due to major checkpoint and events ingestion changes.

## Upgrade to version 0.1.0

1. Disable and delete all inputs.
2. Delete created account(s) under _Configuration_.
3. Download the latest version of Genesys Cloud Add-on for Splunk from its [repository](https://github.com/splunk/genesys_cloud_ta/releases).
4. Install the Genesys Cloud Add-on for Splunk across your deployment.
5. [Configure](../ConfigureAccount/index.md) the Add-on.


# Amazon EventBridge Integration

To ingest additional data from Genesys Cloud, consider leveraging the Genesys Cloud WebSockets notifications via [AWS EventBridge integration](https://developer.genesys.cloud/notificationsalerts/notifications/event-bridge).

This integration is **independent from the Genesys Cloud Add-on for Splunk** and can extend the data collection with more events.

## Genesys Cloud Configuration
For complete information on how to install, configure, and manage an Amazon EventBridge integration, see [About the Amazon EventBridge integration](https://help.mypurecloud.com/?p=227937) in the Genesys Cloud Resource Center.

The Amazon EventBridge integration allows you to receive all events for high-level topics without having to manage subscriptions to a limited list of detailed topics. For more information, see [Available Topics](https://developer.genesys.cloud/notificationsalerts/notifications/available-topics).

### Automation
To automate the provisioning and the configuration of the resources, DevOps engineers or system administrators can leverage this [terraform automation](https://github.com/PierrickLozach/GenesysCloud-Audit-Events-To-Splunk), which will:

- Create a Genesys Cloud EventBridge integration,
- Write audit events from the integration to a Kinesis Stream and an S3 bucket for backup purposes,
- Provide instructions on how to configure Splunk to read events from the Kinesis stream.

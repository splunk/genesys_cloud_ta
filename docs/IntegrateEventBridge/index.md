# Amazon EventBridge Integration

To ingest additional data from Genesys Cloud, consider leveraging the Genesys Cloud WebSockets notifications via [AWS EventBridge integration](https://developer.genesys.cloud/notificationsalerts/notifications/event-bridge).

This integration is **independent from the Genesys Cloud Add-on for Splunk** and can extend the data collection with more events.

## Genesys Cloud Configuration
For complete information on how to install, configure, and manage an Amazon EventBridge integration, see [About the Amazon EventBridge integration](https://help.mypurecloud.com/?p=227937) in the Genesys Cloud Resource Center.

The Amazon EventBridge integration allows you to receive all events for high-level topics without having to manage subscriptions to a limited list of detailed topics. For more information, see [Available Topics](https://developer.genesys.cloud/notificationsalerts/notifications/available-topics).

### Automation
To automate the infrastructure provisioning and the resources configuration, DevOps engineers or system administrators can leverage this [terraform automation](https://splunk.github.io/terraform-genesyscloud-aws), which will:

- Create a Genesys Cloud - AWS EventBridge integration,
- Write events from Genesys Cloud to a Kinesis Stream through an AWS EventBridge bus,
- Configure AWS Firehose to deliver the streamed events to an AWS S3 bucket or to Splunk via HEC.
  > S3 bucket usage is **required** with a Splunk HEC data ingestion.

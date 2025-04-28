# Configure an integration application in Genesys Cloud for the Genesys Cloud Add-on for Splunk

In order to gather data from the Genesys Cloud Platform API using this add-on, you must
first create an OAuth client in Genesys Cloud. This client securely authenticates the Add-on via the
OAuth2 protocol, so that it can access and gather the data according to the services and permission levels that you specify.


## Create an OAuth Client in Genesys Cloud

1. Follow the instructions in the [Genesys Cloud documentation](https://help.mypurecloud.com/articles/create-an-oauth-client/).

2. When creating your client, make a note of the following parameters. They will be needed to [Configure an Account in the Genesys Cloud Add-on for Splunk](../ConfigureAccount/index.md).

    - **Client ID** (Client ID)
    - **Client Secret** (Client Secret)

3. Set the **Grant Types** to **Client Credentials Grant**

4. Set the **OAuth Scopes**. These permissions are required for the Genesys Cloud Add-on for Splunk.

   | API/Permissions name | Scopes     | Description     | API Category              |
   |----------------------|------------|-----------------|---------------------------|
   | `analytics:conversationAggregate:view`  | <ul><li>analytics<li>analytics:readonly</ul> | Read conversation aggregates for your organization. | Analytics |
   | `analytics:conversationDetail:view`  | <ul><li>analytics<li>analytics:readonly</ul> | Read conversation details for your organization. | Analytics |
   | `analytics:queueObservation:view`  | <ul><li>analytics<li>analytics:readonly</ul> | Read query observations for your organization. | Analytics |
   | `analytics:userAggregate:view`  | <ul><li>analytics<li>analytics:readonly</ul> | Read user aggregates for your organization. | Analytics |
   | `routing:queue:view` | <ul><li>routing<li>routing:readonly</ul>   | Read queues for your organization. | Routing |
   | `telephony:plugin:all` | <ul><li>telephony<li>telephony:readonly</ul>  | Read edges, trunks and their metrics as well as phones for your organization. | Telephony Providers Edge   |


5. Click **Save** after you change permissions.

6. Make a note of the generated values.

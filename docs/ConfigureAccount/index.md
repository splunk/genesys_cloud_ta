# Configure an Account in the Genesys Cloud Add-on for Splunk

You must configure at least one Account in the Genesys Cloud Add-on for Splunk.

**Prerequisite:** Before you create an Account, complete the previous step in the configuration process:

- [Configure an integration application in Genesys Cloud for the Genesys Cloud Add-on for Splunk](../ConfigureGenesysCloud/index.md)
- Make sure that port 443 is open to allow the Genesys Cloud Add-on for Splunk to communicate with the Genesys Cloud servers.

## Set up the add-on using Splunk Web

1. Go to the Splunk Web home screen.
2. Click on Genesys Cloud Add-on for Splunk in the left navigation banner.
3. Click on the **Configuration** tab.
4. Under the "Account" section, Click on "Add" and fill in the fields. Use the parameters you configured for the application in the Azure Active Directory, see [Configure an integration application in Genesys Cloud for the Genesys Cloud Add-on for Splunk](../ConfigureGenesysCloud/index.md) where:

   - **Name** is the name given to the Account.
   - **Client ID** is the Client ID from the registered application within Genesys Cloud.
   - **Client Secret** is the registered application key for the corresponding application.
   - **AWS Region** is the AWS Region in which the organization exists and the application was generated.

5. Click **Add** to add the Account to your local configuration.

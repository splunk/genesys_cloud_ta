# Troubleshoot the Genesys Cloud Add-on for Splunk

## General troubleshooting

For troubleshooting tips that you can apply to all add-ons, see [Troubleshoot add-ons](https://docs.splunk.com/Documentation/AddOns/released/Overview/Troubleshootadd-ons) in *Splunk Add-ons*. For additional resources, see [Support and resource links for add-ons](https://docs.splunk.com/Documentation/AddOns/released/Overview/Learnmoreandgethelp) in *Splunk Add-ons*.

## Permission Errors

The `_internal` index reports:

```
Permissions required : [403] Forbidden - Unable to perform the requested action.
You must have at least one of the following permissions assigned:
[integrations:action:view, bridge:actions:view]
```

Please check that the generated Genesys Cloud OAuth client has all needed API permissions and scopes as listed [here](../ConfigureGenesysCloud/index.md#create-an-oauth-client-in-genesys-cloud).

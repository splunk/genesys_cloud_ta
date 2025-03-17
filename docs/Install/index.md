# Install the Genesys Cloud Add-on for Splunk

You can install the Genesys Cloud Add-on for Splunk with Splunk Web or from the command line. You can install the add-on onto any type
of Splunk Enterprise or Splunk Cloud instance (indexer, search head, or forwarder).

1. Download the [Genesys Cloud Add-on for Splunk](https://github.com/splunk/genesys_cloud_ta/releases) from GitHub.
2. Determine where and how to install this add-on in your deployment.
3. Perform any prerequisite steps before installing.
4. Complete your installation.

If you need step-by-step instructions on how to install an add-on in your specific deployment environment, see the [installation walkthrough](#installation-walkthrough) section at the bottom of this page for links to installation instructions specific to a single-instance deployment, distributed deployment, or Splunk Cloud.


## Splunk admin requirements
To install and configure the Genesys Cloud Add-on for Splunk, you must be a member of the `admin` role.


## Distributed installation of this add-on

Use the tables below to determine where and how to install this add-on in a distributed deployment of Splunk Enterprise or any deployment for
which you are using forwarders to get your data in. Depending on your environment, your preferences, and the requirements of the add-on, you
may need to install the add-on in multiple places.

| Splunk instance type | Supported | Required | Comments |
|----|----|----|----|
| Search Heads | Yes | Yes | Install this add-on to all search heads where Genesys Cloud knowledge management is required. Select one node, either a search head or a heavy forwarder, to serve as the configuration server for this add-on, and disable visibility of the add-on in all other locations. |
| Indexers | No | No | Not required, This TA only supports mod input-based data collection which uses a heavy forwarder. |
| Heavy Forwarders | Yes | No | If installed on heavy forwarders, does not need to be installed on indexers. Select one node, either a search head or a heavy forwarder, to serve as the configuration server for this add-on, and disable visibility of the add-on in all other locations. |
| Universal Forwarders | No | No | Universal forwarders are not supported for data collection, because the modular inputs require Python and the Splunk REST handler. |


## Installation walkthrough

See [Installing add-ons](https://docs.splunk.com/Documentation/AddOns/released/Overview/Installingadd-ons) in *Splunk Add-Ons* for detailed instructions describing how to install a Splunk add-on in the following deployment scenarios:

- [Single-instance Splunk Enterprise](http://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall)
- [Distributed Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/released/Overview/Distributedinstall)
- [Splunk Cloud](https://docs.splunk.com/Documentation/AddOns/released/Overview/SplunkCloudinstall)

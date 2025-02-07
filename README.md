# Add-on for Genesys Cloud

## Getting Started
### Installation
TODO
Explain how to install the add-on in Splunk
Point to Splunk official documentation
Which Splunk tier?

### Configuration
TODO
Explain how to configure the add-on
REMEMBER: only admins are supposed to access that tab!

### Usage
TODO
Explain how to configure inputs in the add-on


## Contributing
### Local Development
`ucc-gen build --ta-version 1.0.0` to build the TA

Splunk **locally** running:
* Copy the TA to Splunk Apps directory `cp -R output/genesys_cloud_ta/ $SPLUNK_HOME/etc/apps/`
* Run `https://localhost:8000/en-US/debug/refresh` in case of UI changes
* Restart Splunk if `.conf` files were changed

Splunk **remotely** running (e.g. NOVA):
* Copy / sync the `output/genesys_cloud_ta` folder with the remote splunk instance
    * Currently this symlink is configured in test environment: `$SPLUNK_HOME/etc/apps/genesys_cloud_ta -> /home/splunker/genesys_cloud_ta/output/genesys_cloud_ta/`

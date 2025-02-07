# genesys_cloud_ta

# Getting Started

* If making UI changes -->
    * Build the App: ucc-gen build --ta-version 1.0.0
    * Copy the TA to Splunk Apps directory: cp -R output/genesys_cloud_ta/ $SPLUNK_HOME/etc/apps/
    * Restart Splunk

* If making changes to python file -->
    * symlink output/genesys_cloud_ta to $SPLUNK_HOME/etc/apps
    * Run debug/refresh (https://splunk_url:8000/en-US/debug/refresh)

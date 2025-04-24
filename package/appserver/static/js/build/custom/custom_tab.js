class CustomTab {

    /**
    * Custom Tab
    * @constructor
    * @param {Object} tab - Tab details.
    * @param {element} el - The element of the custom menu.
    */
    constructor(tab, el) {
        this.tab = tab;
        this.el = el;
    }

    render() {
        this.el.innerHTML = `
            <h2 style="margin-top: 20px">${this.tab.title}</h2>
            You can ingest more data by leveraging the Genesys Cloud WebSockets notifications via AWS EventBridge integration.

            <h3>Amazon EventBridge Integration</h3>
            <div>
                Use the Amazon EventBridge integration to store and deliver real-time data from a wide variety of Genesys Cloud events (see <a href="https://developer.genesys.cloud/notificationsalerts/notifications/available-topics" target="_blank" rel="noopener noreferrer">Available topics</a>).
                This integration publishes notifications to a partner event source in your own AWS account, where they are then forwarded to your preferred processing mechanism, including:
                <ul>
                    <li>Lambda</li>
                    <li>Kinesis</li>
                    <li>SQS</li>
                    <li>SNS</li>
                </ul>

                <p>
                    <a href="https://developer.genesys.cloud/notificationsalerts/notifications/event-bridge" target="_blank" rel="noopener noreferrer">More information</a>
                </p>
            </div>
            <h3>Genesys Cloud Configuration</h3>
            <div>
                For complete information on how to install, configure, and manage an Amazon EventBridge integration, see
                <a href="https://developer.genesys.cloud/notificationsalerts/notifications/event-bridge#genesys-cloud-configuration" target="_blank" rel="noopener noreferrer">About the Amazon EventBridge integration</a> in the Genesys Cloud Resource Center.

                <p><b>
                    To automate the provisioning and the configuration of your resources, check this
                    <a href="https://github.com/PierrickLozach/GenesysCloud-Audit-Events-To-Splunk" target="_blank" rel="noopener noreferrer">terraform automation</a>.
                </b></p>
            </div>
        `
    }
}
export default CustomTab;

import import_declare_test

import sys
import json

from splunklib import modularinput as smi

import os
import traceback
import requests
from splunklib import modularinput as smi
from solnlib import conf_manager
from solnlib import log
from solnlib.modular_input import checkpointer
from splunktaucclib.modinput_wrapper import base_modinput  as base_mi 
import PureCloudPlatformClientV2
import splunk.rest

bin_dir  = os.path.basename(__file__)
app_name = os.path.basename(os.path.dirname(os.getcwd()))

class ModInputQUEUE_LOOKUP(base_mi.BaseModInput): 

    def __init__(self):
        use_single_instance = False
        super(ModInputQUEUE_LOOKUP, self).__init__(app_name, "queue_lookup", use_single_instance) 
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = smi.Scheme('queue_lookup')
        scheme.description = 'queue_lookup'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        scheme.add_argument(
            smi.Argument(
                'region',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'account',
                required_on_create=True,
            )
        )
        
        return scheme

    def validate_input(self, definition):
        """validate the input stanza"""
        """Implement your own validation logic to validate the input stanza configurations"""
        pass

    def get_app_name(self):
        return "app_name" 

    def retrieve_queues(helper, routing_api):
        queues_list = []
        page_number = 1
        try:
            while True:
                queues = routing_api.get_routing_queues(page_size = 500, page_number = page_number)
                for queue in queues.entities:
                    queues_list.append(
                        {
                            "id": queue.id,
                            "name": queue.name
                        }
                    )
                if not queues.next_uri:
                    break 
                else:
                    page_number += 1

        except Exception as e:
            helper.log_info(f"Error when calling RoutingApi->get_routing_queues: {e}")
        return queues_list

    def collect_events(helper, ew):
        helper.log_debug("[-] queues lookup input started")

        opt_region = helper.get_arg('region')
        client_id = helper.get_arg("account")["client_id"]
        client_secret = helper.get_arg("account")["client_secret"]

        region = PureCloudPlatformClientV2.PureCloudRegionHosts[opt_region]
        PureCloudPlatformClientV2.configuration.host = region.get_api_host()
        apiclient = (
            PureCloudPlatformClientV2.api_client.ApiClient().get_client_credentials_token(
                client_id, client_secret
            )
        )
        routing_api = PureCloudPlatformClientV2.RoutingApi(apiclient)
        queues_list = ModInputQUEUE_LOOKUP.retrieve_queues(helper, routing_api)
        helper.log_debug("[-] Retrieving queue list ended")

        try:
            # Convert queues_list to JSON format for insertion
            data = json.dumps(queues_list)
            helper.log_debug(f"[-] Data: {data}")

            # Define the lookup collection name. Replace 'queue_observations' with the name of your own lookup if needed.
            lookup_collection = "queues"

            # Construct the REST API URI for the KV Store collection batch_save endpoint.
            # This assumes your app is installed as a Splunk app, under which the lookup resides.
            lookup_uri = f'/servicesNS/nobody/genesys_cloud_ta/storage/collections/data/{lookup_collection}/batch_save'

            helper.log_debug(f"[-] Lookup URI: {lookup_uri}")
            
            # Get the session key from the helper. This session key is necessary to authenticate the REST call.
            session_key = helper.context_meta['session_key']
            helper.log_debug(f"[-] Session Key: {session_key}")
            # Make the REST call
            response, content = splunk.rest.simpleRequest(lookup_uri,
                                                          method='POST',
                                                          sessionKey=session_key,
                                                          jsonargs=data)
            # Debug statements; you can remove these after testing.
            helper.log_debug(f"Queue lookup insertion response status: {response}")
            helper.log_debug(f"Queue lookup insertion response content: {content}")

        except Exception as e:
            helper.log_error(f"Error loading values into the lookup table '{lookup_collection}': {e}")

    def get_account_fields(self):
        account_fields = []
        return account_fields


    def get_checkbox_fields(self):
        checkbox_fields = []
        return checkbox_fields


    def get_global_checkbox_fields(self):
        if self.global_checkbox_fields is None:
            checkbox_name_file = os.path.join(bin_dir, 'global_checkbox_param.json')
            try:
                if os.path.isfile(checkbox_name_file):
                    with open(checkbox_name_file, 'r') as fp:
                        self.global_checkbox_fields = json.load(fp)
                else:
                    self.global_checkbox_fields = []
            except Exception as e:
                self.log_error('Get exception when loading global checkbox parameter names. ' + str(e))
                self.global_checkbox_fields = []
        return self.global_checkbox_fields


if __name__ == '__main__':
    exit_code = ModInputQUEUE_LOOKUP().run(sys.argv)
    sys.exit(exit_code)
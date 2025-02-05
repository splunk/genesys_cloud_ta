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

bin_dir  = os.path.basename(__file__)
app_name = os.path.basename(os.path.dirname(os.getcwd()))

class ModInputQUEUE_OBSERVATIONS(base_mi.BaseModInput): 

    def __init__(self):
        use_single_instance = False
        super(ModInputQUEUE_OBSERVATIONS, self).__init__(app_name, "queue_observations", use_single_instance) 
        self.global_checkbox_fields = None

    def get_scheme(self):
        scheme = smi.Scheme('queue_observations')
        scheme.description = 'queue_observations'
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

    def retrieve_routing_ids(helper, routing_api):
        queue_ids = []
        page_number = 1
        try:
            while True:
                queues = routing_api.get_routing_queues(page_size = 500, page_number = page_number)
                for queue in queues.entities:
                    queue_ids.append(queue.id)
                if not queues.next_uri:
                    break 
                else:
                    page_number += 1

        except Exception as e:
            helper.log_info(f"Error when calling RoutingApi->get_routing_queues: {e}")
        return queue_ids

    def get_active_user(helper, analytics_api, queue_ids):
        body = {
            "filter": {
                "type": "or",
                "clauses": [],
                "predicates": [
                    {
                        "dimension": "queueId",
                        "operator": "matches",
                        "value": queue_id
                    } for queue_id in queue_ids
                ]
            },
            "metrics": ["oActiveUsers", "oAlerting", "oInteracting", "oMemberUsers", "oOffQueueUsers", "oOnQueueUsers", "oUserPresences", "oUserRoutingStatuses", "oWaiting"]  
        }
        page_number = 1
        try:
            response = analytics_api.post_analytics_queues_observations_query(body)
        except Exception as e:
            helper.log_info(f"Error when calling AnalyticsApi->post_analytics_queues_observations_query: {e}")
        return response
    def collect_events(helper, ew):

        helper.log_debug("queue Observations input started")

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
        queue_ids = ModInputQUEUE_OBSERVATIONS.retrieve_routing_ids(helper, routing_api)
        helper.log_debug("Retrieving queue list ended")

        analytics_api = PureCloudPlatformClientV2.AnalyticsApi(apiclient)
        results = ModInputQUEUE_OBSERVATIONS.get_active_user(helper, analytics_api, queue_ids)

        try:
            for result in results.results:
                data = result.data
                group = result.group.get('queueId')
                data_dict = {}

                for item in range(0,len(data)):
                    data_dict[data[item].metric] = data[item].stats.count
                body = {"queueId": group, "data": data_dict}
                event = helper.new_event(
                    source=helper.get_input_type(),
                    index=helper.get_output_index(),
                    sourcetype=helper.get_sourcetype(),
                    data=json.dumps(body)
                )
                ew.write_event(event)
            
        except:
            helper.log_info(f"Error writing genesys_cloud_queueobservations to index: {e}")
        


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
    exit_code = ModInputQUEUE_OBSERVATIONS().run(sys.argv)
    sys.exit(exit_code)
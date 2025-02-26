import PureCloudPlatformClientV2
import logging
from inspect import signature
from typing import List
from PureCloudPlatformClientV2.rest import ApiException
from PureCloudPlatformClientV2.api_client import ApiClient

class GenesysCloudClient:
    client: ApiClient = None

    def __init__(self, logger: logging.Logger, client_id: str, client_secret: str, aws_region: str):
        self.logger = logger
        region = PureCloudPlatformClientV2.PureCloudRegionHosts[aws_region]
        self.host = region.get_api_host()
        self.client_id = client_id
        self.client_secret = client_secret
        self._refresh()

    def _refresh(self):
        self.client = ApiClient(self.host).get_client_credentials_token(
                self.client_id, self.client_secret
            )

    def _fetch(self, api_instance, f_name: str, *args, **kwargs):
        items = []
        enable_pagination = False
        page_number = 1
        page_size = 500

        # Dynamically get the function from the API instance
        function = getattr(api_instance, f_name)

        if not callable(function):
            raise AttributeError(f"{f_name} is not a callable function of the API instance")

        func_signature = signature(function)

        if 'page_number' in func_signature.parameters:
            kwargs['page_number'] = page_number
            kwargs['page_size'] = page_size
            enable_pagination = True

        while True:
            try:
                api_response = function(*args, **kwargs)
                if isinstance(api_response, list):
                    items.extend(api_response)
                else:
                    for item in api_response.entities:
                        items.append(item)

                if not enable_pagination:
                    break
                if not api_response.next_uri:
                    break
                else:
                    page_number += 1
            except ApiException as e:
                # TO BE Confirmed! Haven't hit the limit yet!
                if e.status == 429 and e.reason.contains("Rate limit exceeded the maximum"):
                    self.logger.info("Rate limit exceeded. Refreshing token.")
                    self._refresh()
        return items

    def get(self, api_instance_name: str, function_name: str, *args):
        """
        Fetch data from Genesys Cloud

        :param api_instance_name: Name of the API instance e.g. TelephonyProvidersEdgeApi, RoutingApi, etc
        :param function_name: Name of the function to call in the API instance
        """
        self.logger.info(f"Getting data from {api_instance_name}")
        # Get the API class dynamically
        api_class = getattr(PureCloudPlatformClientV2, api_instance_name)
        # Instantiate the API with the client
        api_instance = api_class(self.client)

        try:
            return self._fetch(api_instance, function_name, *args)
        except AttributeError as e:
            self.logger.err(f"Error: {e}")
        except ApiException as e:
            self.logger.err(f"Exception when calling {api_instance_name}->{function_name}: {e}")

        return []
    
    def post(self, api_instance_name: str, function_name: str, model_name: str, body: dict, *args, **kwargs):
        """
        Sends a POST request to the Genesys Cloud API.

        :param api_instance_name: Name of the API instance, e.g., 'FlowsApi'.
        :param function_name: Name of the function to call in the API instance.
        :param model_name: Name of the data model corresponding to the request body.
        :param body: Dictionary representing the request body.
        """
        self.logger.info(f"Sending data to {api_instance_name} using {function_name}")

        # Dynamically get the API class
        api_class = getattr(PureCloudPlatformClientV2, api_instance_name, None)

        if api_class is None:
            raise AttributeError(f"API class '{api_instance_name}' not found in PureCloudPlatformClientV2")

        # Instantiate the API with the authenticated client
        api_instance = api_class(self.client)

        # Get the function from the API instance
        function = getattr(api_instance, function_name, None)
        if function is None or not callable(function):
            raise AttributeError(f"'{function_name}' is not a valid function of '{api_instance_name}'")

        # Dynamically get the data model class
        model_class = getattr(PureCloudPlatformClientV2, model_name, None)
        if model_class is None:
            raise AttributeError(f"Data model '{model_name}' not found in PureCloudPlatformClientV2")

        # Create an instance of the model
        model_instance = model_class()

        # Assign the values from the 'body' dictionary to the model instance
        for key, value in body.items():
            if hasattr(model_instance, key):
                try:
                    setattr(model_instance, key, value)
                except Exception as e:
                    self.logger.info(f"Exception setting attribute '{key}' in '{model_name}': {e}")
            else:
                self.logger.info(f"The model '{model_name}' does not have a method '{key}'")

        try:
            # Call the function with the model instance and additional arguments
            data = function(model_instance, *args, **kwargs)
            
            return data
        except ApiException as e:
            self.logger.info(f"Exception calling '{api_instance_name}.{function_name}': {e}")
            return None

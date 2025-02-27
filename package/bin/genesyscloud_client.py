import PureCloudPlatformClientV2
import logging
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
        self.client = ApiClient(self.host).get_client_credentials_token(
                self.client_id, self.client_secret
            )

    def _fetch(self, api_instance, f_name: str, *args, **kwargs):
        items = []
        enable_pagination = False
        pagination_params = {"page_number", "page_size", "page_count"}
        page_number = 1

        # Dynamically get the function from the API instance
        function = getattr(api_instance, f_name)

        if not callable(function):
            raise AttributeError(f"{f_name} is not a callable function of the API instance")

        while True:
            api_response = function(*args, **kwargs)

            if isinstance(api_response, list):
                # A simple list (of strings) is returned as response
                items.extend(api_response)
            else:
                # An object such as EdgeEntityListing is returned as response
                enable_pagination = any(key in api_response.attribute_map for key in pagination_params)
                for item in api_response.entities:
                    items.append(item)

            if not enable_pagination:
                break
            if not api_response.next_uri:
                break
            else:
                page_number += 1
                kwargs["page_number"] = page_number
        return items

    def get(self, api_instance_name: str, function_name: str, *args, **kwargs):
        """
        GET data from Genesys Cloud API

        :param api_instance_name: Name of the API instance e.g. TelephonyProvidersEdgeApi, RoutingApi, etc
        :param function_name: Name of the function to call in the API instance
        """
        self.logger.info(f"Getting data from {api_instance_name}")
        # Get the API class dynamically
        api_class = getattr(PureCloudPlatformClientV2, api_instance_name)
        # Instantiate the API with the client
        api_instance = api_class(self.client)

        try:
            return self._fetch(api_instance, function_name, *args, **kwargs)
        except AttributeError as e:
            self.logger.error(f"Error: {e}")
        except ApiException as e:
            if e.status == 429 and e.reason.contains("Rate limit exceeded the maximum"):
                    self.logger.warning("Rate limit exceeded. Refreshing token.")
                    self.client.handle_expired_access_token()
            if e.status == 401 and e.reason.contains("expir"):
                # Haven't hit this yet. Message to be confirmed
                self.logger.warning("Token expired. Refreshing token.")
                self.client.handle_expired_access_token()
            self.logger.error(f"Exception when calling {api_instance_name}->{function_name}: {e}")

        return []

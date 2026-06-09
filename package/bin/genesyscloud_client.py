import PureCloudPlatformClientV2
import logging
import json
import os
import urllib3

from typing import List
from io import BytesIO
from PureCloudPlatformClientV2.rest import ApiException
from PureCloudPlatformClientV2.api_client import ApiClient
from PureCloudPlatformClientV2.configuration import Configuration


class GenesysCloudClient:
    """
    Interface with Genesys Cloud
    """
    def __init__(self, logger: logging.Logger, client_id: str, client_secret: str, aws_region: str, proxy_url: str = None, proxy_username: str = None, proxy_password: str = None):
        self.logger = logger
        if PureCloudPlatformClientV2.PureCloudRegionHosts.__members__.get(aws_region):
            region = PureCloudPlatformClientV2.PureCloudRegionHosts[aws_region]
            self.host = region.get_api_host()
        else:
            self.logger.warning(f"Region {aws_region} not found: searching 'GENESYSCLOUD_HOST' env variable")
            self.host = os.environ.get("GENESYSCLOUD_HOST", None)
            # If host is none, default value will be "https://api.mypurecloud.com"

        # Singleton pattern. Configuration() is a globally shared object.
        # Always set values to avoid data persistance from previous execution.
        config = Configuration()
        config.host = self.host
        config.proxy = proxy_url
        config.proxy_username = proxy_username
        config.proxy_password = proxy_password
        if proxy_url:
            self.logger.info(f"Using proxy: {proxy_url}")

        # Note that passing self.host to the client can be removed as per singleton behavior.
        self.client = ApiClient(self.host).get_client_credentials_token(
            client_id, client_secret
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

        # FIXME add a max_pages safeguard to avoid unbounded pagination
        while True:
            try:
                api_response = function(*args, **kwargs)
            except ApiException as e:
                if e.status in (301, 302, 303, 307, 308):
                    # When getting audit query results API could return a redirect with downloadUrl.
                    body = json.loads(e.body)
                    if "downloadUrl" in body.keys():
                        self.logger.warn(f"Got URL to download events from.")
                        buf = self.download(body["downloadUrl"])
                        for item in json.loads(buf.read()):
                            items.append(item)

                        if "cursor" in body.keys():
                            cursor = body["cursor"]
                            kwargs["cursor"] = cursor
                            continue
                        else:
                            # Nothing else to be fetched
                            break
                    raise
                else:
                    raise

            if isinstance(api_response, list):
                # A simple list (of strings) is returned as response
                items.extend(api_response)
            else:
                # An object such as EdgeEntityListing|RoutingStatus|AuditQueryExecutionResultsResponse|etc is returned
                enable_pagination = any(key in api_response.attribute_map for key in pagination_params)
                if hasattr(api_response, "entities") and api_response.entities:
                    for item in api_response.entities:
                        items.append(item)
                else:
                    items.append(api_response)

            if not enable_pagination:
                break
            if hasattr(api_response, "next_uri") and api_response.next_uri:
                page_number += 1
                kwargs["page_number"] = page_number
            elif hasattr(api_response, "cursor") and api_response.cursor:
                cursor = api_response.cursor
                kwargs["cursor"] = cursor
            else:
                break

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
            if e.status == 429 and "Rate limit exceeded the maximum" in e.reason:
                self.logger.warning("Rate limit exceeded. Refreshing token.")
                self.client.handle_expired_access_token()
            if e.status == 401 and "expir" in e.reason:
                # Haven't hit this yet. Message to be confirmed
                self.logger.warning("Token expired. Refreshing token.")
                self.client.handle_expired_access_token()
            err_message = f"Exception when calling {api_instance_name}->{function_name}:"
            try:
                body = json.loads(e.body)
                message = body["message"]
                self.logger.error(f"{err_message} [{e.status}] {e.reason} - {message}")
            except ValueError as ve:
                self.logger.warning(f"{err_message} {ve}")
                self.logger.error(f"{err_message} [{e.status}] {e.reason} - {e.body}")

        return []

    def download(self, url: str, chunk_size: int = 8192) -> BytesIO:
        """
        Download a URL in chunks into an in-memory buffer.
        :param url: URL to download events from.
        :param chunk_size: Number of bytes to read per iteration.
        :return: BytesIO buffer positioned at the start, containing the downloaded bytes.
        """
        config = Configuration()
        if config.proxy:
            headers = None
            if config.proxy_username and config.proxy_password:
                headers = urllib3.make_headers(
                    proxy_basic_auth=f"{config.proxy_username}:{config.proxy_password}"
                )
            http = urllib3.ProxyManager(config.proxy, proxy_headers=headers)
        else:
            http = urllib3.PoolManager()

        buffer = BytesIO()
        with http.request("GET", url, preload_content=False) as response:
            if response.status != 200:
                raise urllib3.exceptions.HTTPError(f"Unexpected status: {response.status}")
            for chunk in response.stream(chunk_size):
                if chunk:
                    buffer.write(chunk)

        buffer.seek(0)  # rewind so the buffer can be read from the start
        return buffer

    def convert_response(self, response: list, key: str) -> list:
        """
        Convert data returned from paginating POST API.
        :param response: list of objects returned by the API.
        :param key: key of the list of items to be returned (e.g. results, conversations).
        :return: List of items to be ingested.
        """
        total_items = []
        if response is not None:
            for obj in response:
                res_dict = obj.to_dict() or {}
                total_items.extend(res_dict.get(key, []) or [])
        return total_items

    def post(self, api_instance_name: str, function_name: str, model_name: str, body: dict, *args, **kwargs):
        """
        Sends a POST request to the Genesys Cloud API.

        :param api_instance_name: Name of the API instance, e.g., 'FlowsApi'.
        :param function_name: Name of the function to call in the API instance.
        :param model_name: Name of the data model corresponding to the request body.
        :param body: Dictionary representing the request body.
        """
        enable_pagination = False
        api_responses = []
        # Typically 100 items per page is the max accepted
        page_size = 100
        page_number = 1
        total_hits = 0

        # Dynamically get the API class
        api_class = getattr(PureCloudPlatformClientV2, api_instance_name, None)

        if api_class is None:
            self.logger.error(f"AttributeError - API class '{api_instance_name}' not found in PureCloudPlatformClientV2")
            return None

        # Instantiate the API with the authenticated client
        api_instance = api_class(self.client)

        # Get the function from the API instance
        function = getattr(api_instance, function_name, None)
        if function is None or not callable(function):
            self.logger.error(f"AttributeError - '{function_name}' is not a valid function of '{api_instance_name}'")
            return None

        # Dynamically get the data model class
        model_class = getattr(PureCloudPlatformClientV2, model_name, None)
        if model_class is None:
            self.logger.error(f"AttributeError - Data model '{model_name}' not found in PureCloudPlatformClientV2")
            return None

        # Create an instance of the model
        model_instance = model_class()

        # Add paging information to body
        if "paging" in model_instance.attribute_map:
            self.logger.debug(f"Enabling pagination for {function_name} - {model_name}")
            body["paging"] = {
                "pageSize": page_size,
                "pageNumber": page_number
            }
            enable_pagination = True

        if "page_size" in model_instance.attribute_map:
            self.logger.debug(f"Enabling pagination for {function_name} - {model_name}")
            body["page_size"] = page_size
            body["page_number"] = page_number
            enable_pagination = True

        # Assign the values from the 'body' dictionary to the model instance
        for key, value in body.items():
            if hasattr(model_instance, key):
                try:
                    setattr(model_instance, key, value)
                except Exception as e:
                    self.logger.warning(f"Exception setting attribute '{key}' in '{model_name}': {e}")
                    # NOTE: The API call will be executed even if this exception is thrown.
            else:
                self.logger.debug(f"The model '{model_name}' does not have a method '{key}'")

        try:
            # Call the function with the model instance and additional arguments
            while True:
                api_response = function(model_instance, *args, **kwargs)
                api_responses.append(api_response)

                if enable_pagination:
                    if "total_hits" not in api_response.attribute_map:
                        try:
                            total_hits = api_response.total
                        except Exception as e:
                            self.logger.error(f"Pagination enabled but neither 'total_hits' nor 'total' is returned: {api_response.attribute_map}")
                            return None
                    else:
                        total_hits = api_response.total_hits

                    if total_hits - (page_size * page_number) > 0:
                        page_number += 1
                        if "paging" in model_instance.attribute_map:
                            model_instance.paging["pageNumber"] = page_number
                        else:
                            model_instance.page_number = page_number
                        continue
                    break
                return api_response
            return api_responses

        except ApiException as e:
            if e.status == 429 and "Rate limit exceeded the maximum" in e.reason:
                self.logger.warning("Rate limit exceeded. Refreshing token.")
                self.client.handle_expired_access_token()
            if e.status == 401 and "expir" in e.reason:
                # Haven't hit this yet. Message to be confirmed
                self.logger.warning("Token expired. Refreshing token.")
                self.client.handle_expired_access_token()
            err_message = f"Exception when calling {api_instance_name}->{function_name}:"
            try:
                body = json.loads(e.body)
                message = body["message"]
                self.logger.error(f"{err_message} [{e.status}] {e.reason} - {message}")
            except ValueError as ve:
                self.logger.warning(f"{err_message} {ve}")
                self.logger.error(f"{err_message} [{e.status}] {e.reason} - {e.body}")

            return None

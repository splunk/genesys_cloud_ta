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
        Envía una solicitud POST a la API de Genesys Cloud.

        :param api_instance_name: Nombre de la instancia de API, por ejemplo, 'FlowsApi'.
        :param function_name: Nombre de la función a llamar en la instancia de API.
        :param model_name: Nombre del modelo de datos correspondiente al cuerpo de la solicitud.
        :param body: Diccionario que representa el cuerpo de la solicitud.
        :param args: Argumentos posicionales adicionales para la función de la API.
        :param kwargs: Argumentos nombrados adicionales para la función de la API.
        :return: Respuesta de la API.
        """
        self.logger.info(f"Enviando datos a {api_instance_name} usando {function_name}")

        # Obtener la clase de la API dinámicamente
        api_class = getattr(PureCloudPlatformClientV2, api_instance_name, None)

        if api_class is None:
            raise AttributeError(f"No se encontró la clase de API '{api_instance_name}' en PureCloudPlatformClientV2")

        # Instanciar la API con el cliente autenticado
        api_instance = api_class(self.client)

        # Obtener la función de la instancia de API
        function = getattr(api_instance, function_name, None)
        if function is None or not callable(function):
            raise AttributeError(f"'{function_name}' no es una función válida de '{api_instance_name}'")

        # Obtener la clase del modelo de datos dinámicamente
        model_class = getattr(PureCloudPlatformClientV2, model_name, None)
        if model_class is None:
            raise AttributeError(f"No se encontró el modelo de datos '{model_name}' en PureCloudPlatformClientV2")

        # Crear una instancia del modelo
        model_instance = model_class()
        # Asignar los valores del diccionario 'body' a la instancia del modelo
        for key, value in body.items():
            if hasattr(model_instance, key):
                try:
                    setattr(model_instance, key, value)
                except Exception as e:
                    self.logger.info(f"Error setting attribute {key}: {e}")
            else:
                self.logger.info(f"El modelo '{model_name}' no tiene un método '{key}'")

        try:
            # Llamar a la función con el cuerpo y otros argumentos
            return function(model_instance, *args, **kwargs)
        except ApiException as e:
            self.logger.info(f"Excepción al llamar a '{api_instance_name}.{function_name}': {e}")
            return None

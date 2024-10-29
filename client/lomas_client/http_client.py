import requests
from lomas_core.models.requests import LomasRequestModel

from lomas_client.constants import CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT


# pylint: disable=R0903
class LomasHttpClient:
    """A client for interacting with the Lomas API."""

    def __init__(self, url: str, user_name: str, dataset_name: str):
        self.url = url
        self.headers = {"Content-type": "application/json", "Accept": "*/*"}
        self.headers["user-name"] = user_name
        self.dataset_name = dataset_name

    def post(
        self,
        endpoint: str,
        body: LomasRequestModel,
        read_timeout: int = DEFAULT_READ_TIMEOUT,
    ) -> requests.Response:
        """Executes a POST request to endpoint with the provided JSON body.

        Args:
            endpoint (str): The API endpoint to which the request will be sent.
            body_json (dict, optional): The JSON body to include in the POST request.\
                Defaults to {}.
            request_model: (BaseModel, optional): The pydantic model to validate the\
                body_json against. Must be non-null if body_json contains data.
            read_timeout (int): number of seconds that client wait for the server
                to send a response.
                Defaults to DEFAULT_READ_TIMEOUT.

        Returns:
            requests.Response: The response object resulting from the POST request.
        """
        r = requests.post(
            self.url + "/" + endpoint,
            json=body.model_dump(),
            headers=self.headers,
            timeout=(CONNECT_TIMEOUT, read_timeout),
        )
        return r

import logging
import os
from typing import Optional

from opentelemetry.instrumentation.requests import RequestsInstrumentor
from oauthlib.oauth2 import BackendApplicationClient
import requests
from requests_oauthlib import OAuth2Session

from lomas_client.constants import CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT
from lomas_core.models.constants import AuthenticationType
from lomas_core.models.requests import LomasRequestModel


# pylint: disable=R0903
class LomasHttpClient:
    """A client for interacting with the Lomas API."""




    def __init__(
        self,url: str,
        dataset_name: str,
        auth_method: AuthenticationType = AuthenticationType.JWT,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        keycloak_url: Optional[str] = None,
        realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        """Initializes the HTTP client with the specified URL, dataset name and authentication parameters.

        Args:
            url (str): The base URL for the API server.
            dataset_name (str): The name of the dataset to be accessed or manipulated.
            auth_method (AuthenticationType, optional): The authentication method to use
                with the lomas server, one of AuthenticationType. Defaults to AuthenticationType.JWT.
            user_name (str, optional): The name of the user allowed to perform queries, if using
                free pass authentication. Defaults to None.
            user_email (str, optional): The email of the user, if using free passauthentication.
                Defaults to None.
            keycloak_url (str, optional): Overwrites the keycloak url (otherwise passed by
                environment variable), if using jwt authentication. Defaults to None.
            realm (str, optional): Overwrites the realm (otherwise passed by environment variable),
                if using jwt authentication. Defaults to None.
            client_id (str, optional): Overwrites the client id of the user's associated service account
                (otherwise passed by environment variable), if using jwt authentication. Defaults to None.
            client_secret (str, optional): Overwrites the client id of the user's associated service account
                (otherwise passed by environment variable), if using jwt authentication. Defaults to None.
        """
        self.url = url
        self.dataset_name = dataset_name
        self.headers = {"Content-type": "application/json", "Accept": "*/*"}

        match auth_method:
            case AuthenticationType.FREE_PASS:
                if user_name is None or user_email is None:
                    # TODO create client exception
                    raise Exception("Missing user_name and user_email when using freepass authentication method.")
                
                bearer = f'Bearer {{"user_name": "{user_name}", "user_email": "{user_email}"}}'
                self.headers["Authentication"] = bearer

            case AuthenticationType.JWT:
                client_id = client_id or os.getenv("LOMAS_CLIENT_ID") # TODO define const
                client_secret = client_secret or os.getenv("LOMAS_CLIENT_SECRET") # TODO define const
                keycloak_url = keycloak_url or os.getenv("LOMAS_KEYCLOAK_URL") # TODO define const
                realm = realm or os.getenv("LOMAS_REALM") # TODO define const

                if client_id is None or client_secret is None or keycloak_url is None or realm is None:
                    raise Exception("Missing one of client_id, client_secret, keycloak_url or realm when using jwt authentication method.")
                
                self.oauth_client = BackendApplicationClient(client_id=client_id)
                oauth2_session = OAuth2Session(client=self.oauth_client)

                # TODO continue here
                oauth = OAuth2Session(client_id, token=token, auto_refresh_url=refresh_url,
                    auto_refresh_kwargs=extra, token_updater=token_saver)
                r = oauth.get(protected_url)

        RequestsInstrumentor().instrument()

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
        logging.info(
            f"User '{self.headers["user-name"]}' is making a request "
            + f"to url '{self.url}' "
            + f"at the endpoint '{endpoint}' "
            + f"with query params: {body.model_dump()}."
        )
        r = requests.post(
            self.url + "/" + endpoint,
            json=body.model_dump(),
            headers=self.headers,
            timeout=(CONNECT_TIMEOUT, read_timeout),
        )
        return r

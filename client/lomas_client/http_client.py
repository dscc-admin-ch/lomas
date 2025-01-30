import logging
from json import loads
import os
from time import sleep
from typing import Optional

from oauthlib.oauth2 import BackendApplicationClient
from opentelemetry.instrumentation.requests import RequestsInstrumentor
import requests
from requests_oauthlib import OAuth2Session

from lomas_client.constants import CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT
from lomas_core.models.constants import AuthenticationType
from lomas_core.models.requests import LomasRequestModel
from lomas_core.models.responses import Job


# pylint: disable=R0903
class LomasHttpClient:
    """A client for interacting with the Lomas API."""

    def __init__(
        self,
        url: str,
        dataset_name: str,
        auth_method: AuthenticationType = AuthenticationType.JWT,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        keycloak_address: Optional[str] = None,
        keycloak_port: Optional[int] = None,
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
            keycloak_address (str, optional): Overwrites the keycloak address (otherwise passed by
                environment variable), if using jwt authentication. Defaults to None.
            keycloak_port (str, optional): Overwrites the keycloak port (otherwise passed by
                environment variable), if using jwt authentication. Defaults to None.
            realm (str, optional): Overwrites the realm (otherwise passed by environment variable),
                if using jwt authentication. Defaults to None.
            client_id (str, optional): Overwrites the client id of the user's associated service account
                (otherwise passed by environment variable), if using jwt authentication. Defaults to None.
            client_secret (str, optional): Overwrites the client id of the user's associated service account
                (otherwise passed by environment variable), if using jwt authentication. Defaults to None.
        """
        RequestsInstrumentor().instrument()

        self.url = url
        self.dataset_name = dataset_name
        self.headers = {"Content-type": "application/json", "Accept": "*/*"}

        match auth_method:
            case AuthenticationType.FREE_PASS:
                if user_name is None or user_email is None:
                    # TODO create client exception
                    raise Exception(
                        "Missing user_name and user_email when using freepass authentication method."
                    )

                bearer = f'Bearer {{"user_name": "{user_name}", "user_email": "{user_email}"}}'
                self.headers["Authentication"] = bearer

            case AuthenticationType.JWT:
                client_id = client_id or os.getenv("LOMAS_CLIENT_ID")  # TODO define const
                client_secret = client_secret or os.getenv("LOMAS_CLIENT_SECRET")  # TODO define const
                keycloak_address = keycloak_address or os.getenv(
                    "LOMAS_KEYCLOAK_ADDRESS"
                )  # TODO define const
                env_keycloak_port = os.getenv("LOMAS_KEYCLOAK_PORT")
                keycloak_port = keycloak_port or (int(env_keycloak_port) if env_keycloak_port else None) # TODO define const
                realm = realm or os.getenv("LOMAS_REALM")  # TODO define const

                if (
                    client_id is None
                    or client_secret is None
                    or keycloak_address is None
                    or keycloak_port is None
                    or realm is None
                ):
                    raise Exception(
                        "Missing one of client_id, client_secret, keycloak_address, keycloak_port or "
                        "realm when using jwt authentication method."
                    )

                self._client_id = client_id
                self._client_secret = client_secret
                oauth_client = BackendApplicationClient(client_id=self._client_id)
                self._oauth2_session = OAuth2Session(client=oauth_client)
                self._token_endpoint = (
                    f"http://{keycloak_address}:{keycloak_port}/realms/{realm}/protocol/openid-connect/token"
                )

            case _:
                raise Exception(
                    f"Authentication method not supported: {auth_method}"
                )  # TODO make client exception

        self._auth_method = auth_method

    def _fetch_token(self) -> None:
        """Fetches an authorization token and stores it."""
        self._oauth2_session.fetch_token(
            self._token_endpoint, client_id=self._client_id, client_secret=self._client_secret
        )

    def post(
        self,
        endpoint: str,
        body: LomasRequestModel,
        read_timeout: int = DEFAULT_READ_TIMEOUT,
    ) -> requests.Response:
        """Executes a POST request to endpoint with the provided JSON body.

        Handles authorization to the api by automatically fetching a token if required.

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
            f"User '{self.headers.get('user-name')}' is making a request "
            + f"to url '{self.url}' "
            + f"at the endpoint '{endpoint}' "
            + f"with query params: {body.model_dump()}."
        )
        
        match self._auth_method:
            case AuthenticationType.FREE_PASS:
                r = requests.post(
                    self.url + "/" + endpoint,
                    json=body.model_dump(),
                    headers=self.headers,
                    timeout=(CONNECT_TIMEOUT, read_timeout),
                )
                return r

            case AuthenticationType.JWT:
                # Fetch token if not in session yet.
                if not self._oauth2_session.authorized:
                    self._fetch_token()

                try:
                    r = self._oauth2_session.post(
                        self.url + "/" + endpoint,
                        json=body.model_dump(),
                        headers=self.headers,
                        timeout=(CONNECT_TIMEOUT, read_timeout),
                    )
                except TokenExpiredError:
                    # Retry with new token
                    self._fetch_token()
                    r = self._oauth2_session.post(
                        self.url + "/" + endpoint,
                        json=body.model_dump(),
                        headers=self.headers,
                        timeout=(CONNECT_TIMEOUT, read_timeout),
                    )

                return r

            case _:
                raise Exception(
                    f"Authentication method {self._auth_method} not implemented for post."
                )  # TODO internal
            
    def wait_for_job(self, job_uid, n_retry=100, sleep_sec=0.5) -> Job:
        """Periodically query the job endpoint sleeping in between until it completes / times-out."""

        for _ in range(n_retry):
            job_query = requests.get(
                f"{self.url}/status/{job_uid}", headers=self.headers, timeout=(CONNECT_TIMEOUT)
            ).json()

            if job_query["status"] == "complete":
                return Job.model_validate(job_query)

            if (job_err := job_query.get("error")) is not None:
                return Job.model_validate(job_query | {"error": loads(job_err)})

            sleep(sleep_sec)

        raise TimeoutError(f"Job {job_uid} didn't complete in time ({sleep_sec * n_retry})")

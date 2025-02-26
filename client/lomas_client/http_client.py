import logging
import os
from json import loads
from time import sleep
from typing import Optional

import requests
from oauthlib.oauth2 import BackendApplicationClient, TokenExpiredError
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from requests_oauthlib import OAuth2Session

from lomas_client.constants import CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT
from lomas_core.models.requests import LomasRequestModel
from lomas_core.models.responses import Job


# pylint: disable=R0903
class LomasHttpClient:
    """A client for interacting with the Lomas API."""

    def __init__(
        self,
        url: str,
        dataset_name: str,
        keycloak_address: Optional[str] = None,
        keycloak_port: Optional[int] = None,
        keycloak_use_tls: Optional[bool] = None,
        realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        """Initializes the HTTP client with the specified URL, dataset name and authentication parameters.

        Args:
            url (str): The base URL for the API server.
            dataset_name (str): The name of the dataset to be accessed or manipulated.
            keycloak_address (str, optional): Overwrites the keycloak address (otherwise passed by
                environment variable). Defaults to None.
            keycloak_port (str, optional): Overwrites the keycloak port (otherwise passed by
                environment variable). Defaults to None.
            keycloak_use_tls (bool, optional): Overwrites keycloak use_tls (otherwise passed by
                environment variable). Defaults to None.
            realm (str, optional): Overwrites the realm (otherwise passed by environment variable),
                if using jwt authentication. Defaults to None.
            client_id (str, optional): Overwrites the client id of the user's associated service account
                (otherwise passed by environment variable). Defaults to None.
            client_secret (str, optional): Overwrites the client id of the user's associated service account
                (otherwise passed by environment variable). Defaults to None.
        """
        RequestsInstrumentor().instrument()

        self.url = url
        self.dataset_name = dataset_name
        self.headers = {"Content-type": "application/json", "Accept": "*/*"}

        # TODO with issue 407: move these into config.
        client_id = client_id or os.getenv("LOMAS_CLIENT_ID")
        client_secret = client_secret or os.getenv("LOMAS_CLIENT_SECRET")
        keycloak_address = keycloak_address or os.getenv("LOMAS_KEYCLOAK_ADDRESS")
        env_keycloak_port = os.getenv("LOMAS_KEYCLOAK_PORT")
        keycloak_port = keycloak_port or (int(env_keycloak_port) if env_keycloak_port else None)
        env_keycloak_no_tls = os.getenv("LOMAS_KEYCLOAK_USE_TLS") not in [1, "True", "true"]
        keycloak_use_tls = keycloak_use_tls or not env_keycloak_no_tls
        realm = realm or os.getenv("LOMAS_REALM")

        if any(
            x is None
            for x in [client_id, client_secret, keycloak_address, keycloak_port, keycloak_use_tls, realm]
        ):
            raise ValueError(
                "Missing one of client_id, client_secret, keycloak_address, keycloak_port"
                "keycloak_protocol or realm when using jwt authentication method."
            )

        if not keycloak_use_tls:
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        self._client_id = client_id
        self._client_secret = client_secret
        oauth_client = BackendApplicationClient(client_id=self._client_id)
        self._oauth2_session = OAuth2Session(client=oauth_client)
        url_protocol = "https" if keycloak_use_tls else "http"
        self._token_endpoint = (
            f"{url_protocol}://{keycloak_address}:"
            f"{keycloak_port}/realms/{realm}/protocol/openid-connect/token"
        )

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
            f"User (with client id '{self._client_id}') is making a request "
            + f"to url '{self.url}' "
            + f"at the endpoint '{endpoint}' "
            + f"with query params: {body.model_dump()}."
        )

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

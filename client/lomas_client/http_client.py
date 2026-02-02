import os
from time import sleep

import requests
from oauthlib.oauth2 import LegacyApplicationClient, TokenExpiredError
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from requests_oauthlib import OAuth2Session

from lomas_client.constants import CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT, OIDC_CLIENT_ID
from lomas_client.models.config import ClientConfig
from lomas_core.models.constants import init_logging
from lomas_core.models.requests import LomasRequestModel
from lomas_core.models.responses import Job

logger = init_logging(__name__)


class LomasHttpClient:
    """A client for interacting with the Lomas API."""

    def __init__(self, config: ClientConfig) -> None:
        """Initializes the HTTP client with the specified URL, dataset name and authentication parameters."""
        if config.telemetry.enabled:
            RequestsInstrumentor().instrument()

        self.headers = {"Content-type": "application/json", "Accept": "*/*"}
        self.config = config

        if not self.config.keycloak_use_tls or not self.config.lomas_service_use_tls:
            logger.warning(
                "Keycloak or Lomas service configured without TLS -> using oauthlib insecure transport"
            )
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        else:
            # Reset in case it was changed before
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"

        oauth_client = LegacyApplicationClient(OIDC_CLIENT_ID)
        self._oauth2_session = OAuth2Session(client=oauth_client)

        # Fetch first token:
        self._fetch_token()

    def _fetch_token(self) -> None:
        """Fetches an authorization token and stores it."""
        self._oauth2_session.fetch_token(
            str(self.config.oidc_config.token_endpoint),
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
        logger.debug(
            f"User '{self.config.user_name}') is making a request "
            + f"to url '{self.config.app_url}' "
            + f"at the endpoint '{endpoint}' "
            + f"with query params: {body.model_dump()}."
        )

        try:
            r = self._oauth2_session.post(
                f"{self.config.app_url}/{endpoint}",
                json=body.model_dump(),
                headers=self.headers,
                timeout=(CONNECT_TIMEOUT, read_timeout),
            )
        except TokenExpiredError:
            # This also catches if there is no token at first try.
            # Retry with new token
            self._fetch_token()
            r = self._oauth2_session.post(
                f"{self.config.app_url}/{endpoint}",
                json=body.model_dump(),
                headers=self.headers,
                timeout=(CONNECT_TIMEOUT, read_timeout),
            )

        return r

    def wait_for_job(self, job_uid: str, n_retry: int = 1800, sleep_sec: float = 1) -> Job:
        """Periodically query the job endpoint sleeping in between until it completes / times-out."""
        for _ in range(n_retry):
            try:
                job_query = self._oauth2_session.get(
                    f"{self.config.app_url}/status/{job_uid}", headers=self.headers, timeout=(CONNECT_TIMEOUT)
                ).json()
            except TokenExpiredError:
                # This also catches if there is no token at first try.
                self._fetch_token()
                job_query = self._oauth2_session.get(
                    f"{self.config.app_url}/status/{job_uid}", headers=self.headers, timeout=(CONNECT_TIMEOUT)
                ).json()

            # Check for error before accessing "status"
            if "status" in job_query and job_query["status"] in {"complete", "failed"}:
                return Job.model_validate(job_query)

            if "type" in job_query and job_query["type"] == "UnauthorizedAccessException":
                # Handle unauthorized specifically
                self._fetch_token()  # refresh token
                continue  # retry the request

            sleep(sleep_sec)

        raise TimeoutError(f"Job {job_uid} didn't complete in time ({sleep_sec * n_retry})")

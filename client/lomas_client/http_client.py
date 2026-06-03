import json
import tempfile
import time
from pathlib import Path

import requests
from authlib.integrations.requests_client import OAuth2Session, OAuthError
from authlib.oauth2.base import OAuth2Error
from opentelemetry.instrumentation.requests import RequestsInstrumentor

from lomas_client.constants import CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT, OIDC_REQUIRED_SCOPES
from lomas_client.models.config import ClientConfig
from lomas_core.constants import OIDC_LOMAS_CLIENT__CLIENT_ID
from lomas_core.models.config import OIDCDeviceCodeResponse
from lomas_core.models.constants import get_lomas_logger
from lomas_core.models.requests import LomasRequestModel
from lomas_core.models.responses import Job
from lomas_core.utils import url_append

logger = get_lomas_logger(__name__)


class LomasHttpClient:
    """A client for interacting with the Lomas API."""

    def __init__(self, config: ClientConfig) -> None:
        """Initializes the HTTP client with the specified URL, dataset name and authentication parameters."""
        if config.telemetry.enabled:
            RequestsInstrumentor().instrument()

        self.headers = {"Content-type": "application/json", "Accept": "*/*"}
        self.config = config

        if not self.config.oidc_use_tls or not self.config.lomas_service_use_tls:
            logger.warning("OIDC IdP or Lomas service configured without TLS -> using insecure transport")

        self._oauth2_session = OAuth2Session(
            client_id="lomas_client",
            token_endpoint=self.config.oidc_config.token_endpoint,
            scope=OIDC_REQUIRED_SCOPES,
            update_token=self._save_token,
            token=self._load_token(),
            token_endpoint_auth_method="none",
            leeway=30,  # refresh token 30 seconds before expiry
        )

        try:
            self._oauth2_session.refresh_token()
        except (OAuth2Error, OAuthError, AttributeError, requests.HTTPError):
            # Fallback to authorize
            # We catch http errors because dex fails when it cannot link a token to existing user.
            # We catch attribute error in case the token is none
            self._authorize()

    def _get_token_file(self) -> Path:
        """Returns a temp filename for saving/loading the token."""
        return (
            Path(tempfile.gettempdir())
            / f"lomas_{self.config.user_name}_{self.config.dataset_name}_token.json"
        )

    def _save_token(self, token: dict, refresh_token: str | None = None) -> None:
        """Saves the token to disk."""
        self._get_token_file().write_text(json.dumps(token), encoding="utf-8")

    def _load_token(self) -> dict | None:
        """Tries to load the saved token from disk."""
        if self._get_token_file().is_file():
            return json.loads(self._get_token_file().read_text(encoding="utf-8"))
        return None

    def _authorize(self) -> None:
        """Chooses the right grant and gets access token."""
        if self.config.use_password_flow:
            self._password_flow()
        else:
            self._device_flow()

    def _password_flow(self) -> None:
        """Performs a legacy password flow to fetch an access token."""
        self._oauth2_session.fetch_token(
            self.config.oidc_config.token_endpoint,
            username=self.config.user_name,
            password=self.config.user_password,
            grant_type="password",
        )

    def _device_flow(self) -> None:
        """Fetches an access token using the device auth flow.

        Waits until the user has authorized the python client.

        Raises:
            TimeoutError: In case the user did not authorize the Lomas Python client in time.
        """
        print("Authorizing Lomas Python client")

        device_data_resp = requests.post(
            str(self.config.oidc_config.device_authorization_endpoint),
            data={"client_id": OIDC_LOMAS_CLIENT__CLIENT_ID, "scope": OIDC_REQUIRED_SCOPES},
        )
        device_data_resp.raise_for_status()
        device_data = OIDCDeviceCodeResponse.model_validate(device_data_resp.json())

        if not device_data.verification_uri_complete:
            print(f"Go to: {device_data.verification_uri}")
            print(f"Log in and authorize the Lomas Python client with this code {device_data.user_code}")
        else:
            print(f"Go to: {device_data.verification_uri_complete}")
            print("Log in and authorize the Lomas Python client.")

        print("This will hang until the authorization is complete...")

        interval = 5
        while True:
            try:
                self._oauth2_session.fetch_token(
                    self.config.oidc_config.token_endpoint,
                    grant_type="urn:ietf:params:oauth:grant-type:device_code",
                    device_code=device_data.device_code,
                )
                break
            except (OAuth2Error, OAuthError) as e:
                if e.error == "authorization_pending":
                    time.sleep(interval)
                elif e.error == "slow_down":
                    interval += 5
                    time.sleep(interval)
                elif e.error == "expired_token":
                    raise TimeoutError("Lomas Python client was not authorized soon enough.") from e
                else:
                    raise e

        print("Authorization process complete.")

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
            body (LomasRequestModel): The body to include in the POST request.
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
                url_append(self.config.app_url, endpoint),
                json=body.model_dump(),
                headers=self.headers,
                timeout=(CONNECT_TIMEOUT, read_timeout),
            )
        except OAuth2Error:
            # Handle expired refresh token
            self._authorize()

            r = self._oauth2_session.post(
                url_append(self.config.app_url, endpoint),
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
                    url_append(self.config.app_url, f"/status/{job_uid}"),
                    headers=self.headers,
                    timeout=(CONNECT_TIMEOUT),
                ).json()
            except OAuth2Error:
                # Handle expired refresh token
                self._authorize()
                job_query = self._oauth2_session.get(
                    url_append(self.config.app_url, f"/status/{job_uid}"),
                    headers=self.headers,
                    timeout=(CONNECT_TIMEOUT),
                ).json()
            # Check for error before accessing "status"
            if "status" in job_query and job_query["status"] in {"complete", "failed"}:
                return Job.model_validate(job_query)

            time.sleep(sleep_sec)

        raise TimeoutError(f"Job {job_uid} didn't complete in time ({sleep_sec * n_retry})")

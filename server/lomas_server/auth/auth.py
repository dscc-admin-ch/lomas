from functools import cached_property
from typing import Annotated, Literal

import jwt
import requests
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes
from pydantic import BaseModel, Field, HttpUrl

from lomas_core.constants import Scopes
from lomas_core.error_handler import UnauthorizedAccessException
from lomas_core.models.collections import UserId
from lomas_core.models.config import OIDCConfig
from lomas_core.models.constants import AuthenticationType, init_logging
from lomas_server.constants import OIDCClaims

logger = init_logging(__name__)


class FreePassAuthenticator(BaseModel):
    """Authenticator that Bypass Auth."""

    authentication_type: Literal[AuthenticationType.FREE_PASS]


class OIDCAuthenticator(BaseModel):
    """Authenticator that identifies users by either validating the provided JWT token querying the userinfo endpoint."""

    authentication_type: Literal[AuthenticationType.OIDC]
    """The OpenId connect provider's discovery url"""
    oidc_discovery_url: HttpUrl
    """Whether to use the access token to query userinfo endpoint. If false, access token is parsed as jwt."""
    query_userinfo: bool

    # TODO add ttl to cache?
    @cached_property
    def oidc_config(self) -> OIDCConfig:
        """Returns the oidc provider config."""
        response = requests.get("{self.oidc_discovery_url}")
        response.raise_for_status()

        return OIDCConfig.model_validate_json(response.json())

    @cached_property
    def jwk_client(self) -> jwt.PyJWKClient:
        """Initializes instance PyJWKClient with caching."""
        return jwt.PyJWKClient(
            str(self.oidc_config.jwks_uri),
            cache_keys=True,
        )


# Ideally should be at the top of the file with forward type reference but oh well
AuthenticatorT = Annotated[
    FreePassAuthenticator | OIDCAuthenticator, Field(discriminator="authentication_type")
]


def get_user_id(
    authenticator: AuthenticatorT, security_scopes: SecurityScopes, auth_creds: HTTPAuthorizationCredentials
) -> UserId:
    """Extracts user id from bearer token.

    Args:
        security_scopes (SecurityScopes): The required scopes for the endpoint.
        auth_creds (HTTPAuthorizationCredentials): Authorization credentials.

    Returns:
        UserId: The UserId object containing user infos.
    """
    match authenticator:
        case FreePassAuthenticator():
            try:
                if Scopes.ADMIN in security_scopes.scopes:
                    # Admins don't come with proper user id, so we create a dummy one.
                    user = UserId(name="admin", email="admin@example.com")
                else:
                    user = UserId.model_validate_json(auth_creds.credentials)
            except Exception as e:
                raise UnauthorizedAccessException("Failed bearer token verification.") from e

        case OIDCAuthenticator():
            try:
                # Get userfinfo from userinfo endpoint or jwt token
                if authenticator.query_userinfo:
                    response = requests.get(
                        url=str(authenticator.oidc_config.userinfo_endpoint),
                        headers={"Authorization": f"Bearer {auth_creds.credentials}"},
                    )
                    response.raise_for_status()
                    userinfo = response.json()

                else:
                    # Extracts kid from JWT and fetches corresponding key from keycloak (or cache).
                    key = authenticator.jwk_client.get_signing_key_from_jwt(auth_creds.credentials)
                    # Decodes and validates JWT
                    userinfo = jwt.decode(auth_creds.credentials, key=key)

                # Reconstruct user id
                if Scopes.ADMIN in security_scopes.scopes:
                    # We use only one generic admin for now
                    if (
                        userinfo[OIDCClaims.USER_NAME] != "lomas_admin"
                    ):  # TODO need to add admin role/scope see issue 399 or match admin users against database.
                        raise UnauthorizedAccessException("Only admin user can query this endpoint.")
                    user = UserId(name="admin", email="noemailexample.com")
                else:
                    user = UserId(
                        name=userinfo[
                            OIDCClaims.USER_NAME
                        ],  # TODO make pydantic model or parametrize claim name?
                        email=userinfo[OIDCClaims.USER_EMAIL],
                    )
            except UnauthorizedAccessException as e:
                raise e
            except Exception as e:
                # TODO problematic to add e into error message to client?
                raise UnauthorizedAccessException("Failed bearer token verification.") from e

    return user

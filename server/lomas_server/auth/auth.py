from functools import cached_property
from typing import Annotated, Literal

import jwt
import requests
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes
from pydantic import BaseModel, Field, HttpUrl

from lomas_core.constants import OIDC_LOMAS_CLIENT__CLIENT_ID, Scopes
from lomas_core.error_handler import InternalServerException, UnauthorizedAccessException
from lomas_core.models.collections import UserId
from lomas_core.models.config import OIDCConfig
from lomas_core.models.constants import AuthenticationType, init_logging
from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.constants import OIDCClaims

logger = init_logging(__name__)


class FreePassAuthenticator(BaseModel):
    """Authenticator that Bypass Auth."""

    authentication_type: Literal[AuthenticationType.FREE_PASS]


class OIDCAuthenticator(BaseModel):
    """Authenticator that identifies users by either validating the provided JWT token querying the userinfo endpoint."""

    authentication_type: Literal[AuthenticationType.OIDC]
    """The OpenId connect provider's discovery url."""
    oidc_discovery_url: HttpUrl
    """Whether to use the access token to query userinfo endpoint.

    If false, access token is parsed as jwt.
    """
    query_userinfo: bool

    # TODO add ttl to cache?
    @cached_property
    def oidc_config(self) -> OIDCConfig:
        """Returns the oidc provider config."""
        response = requests.get(str(self.oidc_discovery_url))
        response.raise_for_status()

        return OIDCConfig.model_validate(response.json())

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


def get_user_id(authenticator: AuthenticatorT, auth_creds: HTTPAuthorizationCredentials) -> UserId:
    """Extracts user id from bearer token.

    Fails if user does not have scope.

    Args:
        authenticator (AuthenticatorT): A valid authenticator (FreePassAuthenticator or OIDC Authenticator)
        security_scopes (SecurityScopes): The required scopes for the endpoint.
        auth_creds (HTTPAuthorizationCredentials): Authorization credentials.

    Returns:
        UserId: The UserId object containing user infos.
    """
    match authenticator:
        case FreePassAuthenticator():
            try:
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
                    # Note: audience is set to lomas client because it receives the token from IdP. Not all IdP support multi-audience.
                    userinfo = jwt.decode(
                        auth_creds.credentials, key=key, audience=OIDC_LOMAS_CLIENT__CLIENT_ID
                    )

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


def authorize_user(user: UserId, admin_database: AdminDatabase, security_scopes: SecurityScopes) -> None:
    """Raises an UnauthorizedAccessExpection if the user does not have the permission for the given scopes.

    Also raises an exception if an unknown scope is required.

    Args:
        user (UserId): The user id object
        admin_database (AdminDatabase): The admin database to get user permissions from.
        security_scopes (SecurityScopes): The required scopes.
    """
    for scope in security_scopes.scopes:
        match scope:
            case Scopes.ADMIN:
                if not admin_database.is_user_admin(user.name):
                    raise UnauthorizedAccessException("Only admin users can query this endpoint.")
            case _:
                # Raise server exception if scope is unknown
                raise InternalServerException(f"Unknown security scope {scope}, cannot authorize query.")

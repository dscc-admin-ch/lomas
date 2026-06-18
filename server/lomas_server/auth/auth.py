from functools import cached_property
from typing import Annotated, Any, Literal

import jwt
import requests
from fastapi.security import SecurityScopes
from pydantic import BaseModel, Field, HttpUrl

from lomas_core.constants import OIDC_LOMAS_CLIENT__CLIENT_ID, Scopes
from lomas_core.exceptions import InternalServerException, UnauthorizedAccessException
from lomas_core.models.collections import UserId
from lomas_core.models.config import OIDCConfig
from lomas_core.models.constants import AuthenticationType, get_lomas_logger
from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.constants import OIDCClaims

logger = get_lomas_logger(__name__)


class FreePassAuthenticator(BaseModel):
    """Authenticator that Bypass Auth."""

    authentication_type: Literal[AuthenticationType.FREE_PASS]

    def __init__(self, **data: Any) -> None:
        logger.warning("Using FreePassAuthenticator, not safe for production!")
        super().__init__(**data)

    def get_user_id(self, credentials: str) -> UserId:
        """Extracts user id from bearer token.

        Fails if user does not have scope.

        Args:
            authenticator (AuthenticatorT): A valid authenticator (FreePassAuthenticator or OIDC Authenticator)
            credentials (str): Authorization credentials.

        Returns:
            UserId: The UserId object containing user infos.
        """
        try:
            return UserId(name=credentials, email="free@pass.com")
        except Exception as e:
            raise UnauthorizedAccessException("Failed bearer token verification.") from e


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

    def get_user_id(self, credentials: str) -> UserId:
        """Extracts user id from bearer token.

        Fails if user does not have scope.

        Args:
            authenticator (AuthenticatorT): A valid authenticator (FreePassAuthenticator or OIDC Authenticator)
            credentials (str): Authorization credentials.

        Returns:
            UserId: The UserId object containing user infos.
        """
        try:
            # Get userfinfo from userinfo endpoint or jwt token
            if self.query_userinfo:
                response = requests.get(
                    url=str(self.oidc_config.userinfo_endpoint),
                    headers={"Authorization": f"Bearer {credentials}"},
                )
                response.raise_for_status()
                userinfo = response.json()

            else:
                # Extracts kid from JWT and fetches corresponding key from keycloak (or cache).
                key = self.jwk_client.get_signing_key_from_jwt(credentials)
                # Decodes and validates JWT
                # Note: audience is set to lomas client because it receives the token from IdP. Not all IdP support multi-audience.
                userinfo = jwt.decode(credentials, key=key, audience=OIDC_LOMAS_CLIENT__CLIENT_ID)

            return UserId(
                name=userinfo[OIDCClaims.USER_NAME],  # TODO make pydantic model or parametrize claim name?
                email=userinfo[OIDCClaims.USER_EMAIL],
            )

        except UnauthorizedAccessException as e:
            raise e
        except Exception as e:
            # TODO problematic to add e into error message to client?
            raise UnauthorizedAccessException("Failed bearer token verification.") from e


# Ideally should be at the top of the file with forward type reference but oh well
AuthenticatorT = Annotated[
    FreePassAuthenticator | OIDCAuthenticator, Field(discriminator="authentication_type")
]


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

from functools import cached_property
from typing import Annotated, Literal

import jwt
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes
from pydantic import BaseModel, Field, HttpUrl

from lomas_core.constants import Scopes
from lomas_core.error_handler import UnauthorizedAccessException
from lomas_core.models.collections import UserId
from lomas_core.models.constants import AuthenticationType, init_logging
from lomas_server.constants import KCAttributeNames

logger = init_logging(__name__)


class FreePassAuthenticator(BaseModel):
    """Authenticator that Bypass Auth."""

    authentication_type: Literal[AuthenticationType.FREE_PASS]


class JWTAuthenticator(BaseModel):
    """Authenticator that identifies users by validating the provided JWT token."""

    authentication_type: Literal[AuthenticationType.JWT]
    """The keycloak address for this app instance."""
    keycloak_url: HttpUrl
    """Realm: The realm name for this app instance."""
    realm: str

    @cached_property
    def jwk_client(self) -> jwt.PyJWKClient:
        """Initializes instance PyJWKClient with caching."""
        return jwt.PyJWKClient(
            f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/certs",
            cache_keys=True,
        )


# Ideally should be at the top of the file with forward type reference but oh well
AuthenticatorT = Annotated[
    FreePassAuthenticator | JWTAuthenticator, Field(discriminator="authentication_type")
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

        case JWTAuthenticator():
            try:
                # Extracts kid from JWT and fetches corresponding key from keycloak (or cache).
                key = authenticator.jwk_client.get_signing_key_from_jwt(auth_creds.credentials)
                # Decodes and validates JWT
                token_content = jwt.decode(auth_creds.credentials, key=key)

                if Scopes.ADMIN in security_scopes.scopes:
                    # We use only one generic admin for now
                    if (
                        token_content["client_id"] != "lomas_admin"
                    ):  # TODO need to add admin role/scope see issue 399
                        raise UnauthorizedAccessException("Only admin user can query this endpoint.")
                    user = UserId(name="admin", email="noemailexample.com")
                else:
                    user = UserId(
                        name=token_content[KCAttributeNames.USER_NAME],
                        email=token_content[KCAttributeNames.USER_EMAIL],
                    )
            except UnauthorizedAccessException as e:
                raise e
            except Exception as e:
                # TODO problematic to add e into error message to client?
                raise UnauthorizedAccessException("Failed bearer token verification.") from e

    return user

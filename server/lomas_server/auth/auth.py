from abc import ABC
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes

from lomas_core.constants import Scopes
from lomas_core.error_handler import InternalServerException, UnauthorizedAccessException
from lomas_core.models.collections import UserId
from lomas_core.models.config import AuthenticatorConfig, FreePassAuthenticatorConfig, JWTAuthenticatorConfig


class UserAuthenticator(ABC):
    """Abstract base class for providing user authentification methods."""

    def get_user_id(
        self,
        auth_creds: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    ) -> UserId:
        """Extracts user id from bearer token.

        Args:
            auth_creds (Annotated[HTTPAuthorizationCredentials, Depends): Authorization credentials.

        Returns:
            UserId: The UserId object containing user infos.
        """


class FreePassAuthenticator(UserAuthenticator):
    """Authenticator class that simply extracts user information from.

    the provided bearer.
    ! No verification is performed!
    """

    def get_user_id(
        self,
        security_scopes: SecurityScopes,
        auth_creds: HTTPAuthorizationCredentials #Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    ) -> UserId:
        """Parses the HTTP bearer token as a json string to construct a UserId.

        !Does NOT perform any verification!

        Args:
            security_scopes (SecurityScopes): The required scopes for the endpoint.
            auth_creds (Annotated[HTTPAuthorizationCredentials, Depends): The HTTP credentials.

        Returns:
            UserId: The parsed UserId.
        """
        try:
            if Scopes.ADMIN in security_scopes.scopes:
                # Admins don't come with proper user id, so we create a dummy one.
                user = UserId(name="admin", email="admin@example.com")
            else:
                user = UserId.model_validate_json(auth_creds.credentials)
        except Exception as e:
            raise UnauthorizedAccessException("Failed bearer token verification.") from e

        return user


class JWTAuthenticator(UserAuthenticator):
    """Authenticator class that identifies users by validating the provided JWT token."""

    def __init__(self, keycloak_address: str, keycloak_port: int, keycloak_use_tls: bool, realm: str):
        """Constructor method.

        Initializes instance PyJWKClient with caching.

        Args:
            keycloak_address (str): The keycloak address for this app instance.
            keycloak_port (int): The keycloak port
            keycloak_verify_tls (str): Whether to use tls or not for interacting with keycloak.
            realm (str): The realm name for this app instance.
        """
        url_protocol = "https" if keycloak_use_tls else "http"

        self.jwk_client = jwt.PyJWKClient(
            (
                f"{url_protocol}://{keycloak_address}:{keycloak_port}/"
                f"realms/{realm}/protocol/openid-connect/certs"
            ),
            cache_keys=True,
        )

    def get_user_id(
        self,
        security_scopes: SecurityScopes,
        auth_creds: HTTPAuthorizationCredentials #Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    ) -> UserId:
        """Parses the JWT bearer token to construct a UserId.

        The JWT is verified against the certificates provided by the Id Provider.

        ! Does not verify scopes yet !

        Args:
            security_scopes (SecurityScopes): The required scopes for the endpoint.
            auth_creds (Annotated[HTTPAuthorizationCredentials, Depends): The HTTP credentials.

        Returns:
            UserId: The parsed UserId.
        """
        try:
            # Extracts kid from JWT and fetches corresponding key from keycloak (or cache).
            key = self.jwk_client.get_signing_key_from_jwt(auth_creds.credentials)
            # Decodes and validates JWT
            token_content = jwt.decode(auth_creds.credentials, key=key)
            print(token_content)
            if Scopes.ADMIN in security_scopes.scopes:
                # We use only one generic admin for now
                if token_content["client_id"] != "lomas_admin": # TODO need to add admin role/scope see issue 399
                    raise UnauthorizedAccessException("Only admin user can query this endpoint.")
                user = UserId(name="admin", email="noemailexample.com")
            else:
                user = UserId(name=token_content["user_name"], email=token_content["user_email@example.com"])

        except Exception as e:
            # TODO problematic to add e into error message to client?
            print(e)
            raise UnauthorizedAccessException("Failed bearer token verification.") from e

        return user


def authenticator_factory(auth_config: AuthenticatorConfig) -> UserAuthenticator:
    """Creates an instance of a UserAuthenticator from the provided config.

    Args:
        auth_config (AuthenticatorConfig): The configuration to create the authenticator.

    Raises:
        InternalServerException: If it cannot create the authenticator.

    Returns:
        UserAuthenticator: The correct authenticator instance.
    """
    match auth_config:
        case FreePassAuthenticatorConfig():
            return FreePassAuthenticator()
        case JWTAuthenticatorConfig():
            return JWTAuthenticator(
                auth_config.keycloak_address,
                auth_config.keycloak_port,
                auth_config.keycloak_use_tls,
                auth_config.realm,
            )
        case _:
            raise InternalServerException("Authenticator type not supported.")

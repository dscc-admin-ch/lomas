import logging
from abc import ABC, abstractmethod

import jwt
from fastapi.security import HTTPAuthorizationCredentials, SecurityScopes
from pydantic import HttpUrl

from lomas_core.constants import Scopes
from lomas_core.error_handler import UnauthorizedAccessException
from lomas_core.models.collections import UserId
from lomas_server.constants import KCAttributeNames


class UserAuthenticator(ABC):
    """Abstract base class for providing user authentification methods."""

    @abstractmethod
    def get_user_id(
        self,
        security_scopes: SecurityScopes,
        auth_creds: HTTPAuthorizationCredentials,
    ) -> UserId:
        """Extracts user id from bearer token.

        Args:
            security_scopes (SecurityScopes): The required scopes for the endpoint.
            auth_creds (HTTPAuthorizationCredentials): Authorization credentials.

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
        auth_creds: HTTPAuthorizationCredentials,
    ) -> UserId:
        """Parses the HTTP bearer token as a json string to construct a UserId.

        !Does NOT perform any verification!

        Args:
            security_scopes (SecurityScopes): The required scopes for the endpoint.
            auth_creds (HTTPAuthorizationCredentials): Authorization credentials.

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

        logging.info(f"Authenticated user {user.name}")
        return user


class JWTAuthenticator(UserAuthenticator):
    """Authenticator class that identifies users by validating the provided JWT token."""

    def __init__(self, keycloak_url: HttpUrl, realm: str) -> None:
        """Constructor method.

        Initializes instance PyJWKClient with caching.

        Args:
            keycloak_address (str): The keycloak address for this app instance.
            keycloak_port (int): The keycloak port
            keycloak_use_tls (str): Whether to use tls or not for interacting with keycloak.
            realm (str): The realm name for this app instance.
        """
        self.jwk_client = jwt.PyJWKClient(
            f"{keycloak_url}/realms/{realm}/protocol/openid-connect/certs",
            cache_keys=True,
        )

    def get_user_id(
        self,
        security_scopes: SecurityScopes,
        auth_creds: HTTPAuthorizationCredentials,
    ) -> UserId:
        """Parses the JWT bearer token to construct a UserId.

        The JWT is verified against the certificates provided by the Id Provider.

        ! Does not verify scopes yet !

        Args:
            security_scopes (SecurityScopes): The required scopes for the endpoint.
            auth_creds (HTTPAuthorizationCredentials): Authorization credentials.

        Returns:
            UserId: The parsed UserId.
        """
        try:
            # Extracts kid from JWT and fetches corresponding key from keycloak (or cache).
            key = self.jwk_client.get_signing_key_from_jwt(auth_creds.credentials)
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

        except Exception as e:
            # TODO problematic to add e into error message to client?
            raise UnauthorizedAccessException("Failed bearer token verification.") from e

        logging.info(f"Authenticated user {user.name}")
        return user

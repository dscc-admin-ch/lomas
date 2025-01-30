from abc import ABC
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from lomas_core.models.collections import UserId


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
        auth_creds: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
    ) -> UserId:
        """Parses the HTTP bearer token as a json string to construct a UserId.

        !Does NOT perform any verification!

        Args:
            auth_creds (Annotated[HTTPAuthorizationCredentials, Depends): The HTTP credentials.

        Returns:
            UserId: The parsed UserId.
        """
        return UserId.model_validate_json(auth_creds.credentials)

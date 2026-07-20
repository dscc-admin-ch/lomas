import uuid
from pathlib import Path

import bcrypt
import grpc
import yaml
from returns.io import IOResultE, IOSuccess, impure_safe
from returns.iterables import Fold

from lomas_core.models.collections import UserCollection
from lomas_core.models.constants import get_lomas_logger
from lomas_server.administration.dex.api.api_pb2 import (
    CreatePasswordReq,
    DeletePasswordReq,
    ListPasswordReq,
    Password,
    UpdatePasswordReq,
)
from lomas_server.administration.dex.api.api_pb2_grpc import DexStub
from lomas_server.models.config import DexAdminConfig

logger = get_lomas_logger(__name__)


class InvalidDexOperation(Exception):
    """Groups all exceptions for trying to perform invalid Dex rpcs (e.g. adding a user that already exists)."""

    def __init__(self, error_message: str) -> None:
        """Init function.

        Args:_description_
            error_message (str): initial error message
        """
        self.error_message = error_message


class DexRPCError(Exception):
    """Groups all Dex rpc errors."""

    def __init__(self, error_message: str) -> None:
        """Init function.

        Args:_description_
            error_message (str): initial error message
        """
        self.error_message = error_message


def get_grpc_channel(dex_config: DexAdminConfig) -> grpc.Channel:
    """Returns a valid grpc channel to use as context.

    Note: does not support mTLS yet.

    Args:
        dex_config (DexAdminConfig): The Dex config

    Returns:
        grpc.Channel: A valid grpc channel.
    """
    assert dex_config.use_mtls is False
    return grpc.insecure_channel(f"{dex_config.url.host}:{dex_config.url.port}")


def hash_pwd(password: str) -> bytes:
    """Hashes the password string.

    Args:  repeated Password passwords = 1;
        password (str): The password string to hash.

    Returns:
        bytes: The password hash.
    """
    bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes, salt)

    return hash


def to_log(user_provided_str: str) -> str:
    """Util function to sanitize user provided strings before logging.

    Args:
        user_provided_str (str): User provided string to sanitize

    Returns:
        str: The sanitized string.
    """
    return user_provided_str.replace("\r\n", "").replace("\n", "")


@impure_safe
def add_dex_user(dex_config: DexAdminConfig, user_name: str, user_email: str, user_password: str) -> str:
    """Adds a new user to dex.

    Args:
        dex_config (DexAdminConfig): The DexAdminConfig
        user_name (str): The user name
        user_email (str): The user email
        user_password (str): The user pasword

    Raises:
        InvalidDexOperation: If the user already exists.
        e: grpc.RpcError
    """
    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)

        new_pwd = Password(
            email=user_email, hash=hash_pwd(user_password), username=user_name, user_id=str(uuid.uuid4())
        )

        res = stub.CreatePassword(CreatePasswordReq(password=new_pwd))

        if res.already_exists:
            msg = f"Failed to add user {to_log(user_name)} with email {to_log(user_email)}. User or email already exists."
            logger.error(msg)
            raise InvalidDexOperation(msg)

        logger.debug(f"Added {to_log(user_name)} user.")
        return user_name


@impure_safe
def del_dex_user(dex_config: DexAdminConfig, user_name: str) -> bool:
    """Removes the dex user.

    Args:
        dex_config (DexAdminConfig): The DexAdminConfig
        user_name (str): The name of the user to remove.

    Raises:
        InvalidDexOperation: If the user does not exist.
        e: grpc.RpcError
    """
    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)

        dex_users = stub.ListPasswords(ListPasswordReq()).passwords

        for user in dex_users:
            if user.username == user_name:
                res = stub.DeletePassword(DeletePasswordReq(email=user.email))
                logger.debug(f"Deleted dex user {user_name}")
                return not res.not_found

        logger.error(f"User {user_name} does not exist.")
        raise InvalidDexOperation(f"Cannot delete. User does not exist {user_name}")


@impure_safe
def del_all_dex_users(dex_config: DexAdminConfig) -> None:
    """Removes all dex users.

    Args:
        dex_config (DexAdminConfig): The DexAdminConfig

    Raises:
        grpc.RpcError: If any of the calls to dex fails
    """
    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)
        dex_users = stub.ListPasswords(ListPasswordReq()).passwords

        for user in dex_users:
            stub.DeletePassword(DeletePasswordReq(email=user.email))
            logger.debug(f"Deleted dex user {user.username}")

    logger.debug("Removed all dex users.")


@impure_safe
def add_dex_users(
    dex_config: DexAdminConfig,
    user_list: UserCollection,
    clean: bool,
    overwrite: bool,
) -> list[str]:
    """Adds new lomas users to Dex.

    Iterates over `user_list` and creates password entries in Dex for each user.
    If `clean` is True all existing dex users are removed first. If `overwrite`
    is True (and not `clean`) any existing dex users with the same username are
    removed before creating the new entry.

    Args:
        dex_config (DexAdminConfig): A DexAdminConfig
        user_list (UserCollection): Collection to load the users from
        clean (bool): Whether to remove existing users and start with a clean state.
        overwrite(bool): Whether to overwrite existing users.

    Raises:
        InvalidDexOperation: If a user does not have a password or the user already exists and should not be overwritten.
        grpc.RpcError: If any of the calls to dex fails
    """
    # Remove all existing users if requested
    if clean:
        del_all_dex_users(dex_config)

    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)
        dex_users = stub.ListPasswords(ListPasswordReq()).passwords

        added_user_result: list[IOResultE] = []
        for user in user_list.users:
            # Remove user with same name if requested (but not already cleaned)
            if overwrite and not clean:
                for dex_user in dex_users:
                    if dex_user.username == user.id.name:
                        stub.DeletePassword(DeletePasswordReq(email=dex_user.email))
                        logger.debug(f"Removed existing dex user {user.id.name} due to overwrite flag")

            # Create the dex user
            # TODO replace client_secret with password
            if user.id.client_secret is None:
                logger.error(f"Cannot add Dex user {user.id.name} without password")
                raise InvalidDexOperation(f"Cannot add Dex user {user.id.name} without password")

            added_user = add_dex_user(dex_config, user.id.name, user.id.email, user.id.client_secret)
            added_user_result.append(added_user)
        logger.debug("Added dex users from user collection.")
        return Fold.collect(added_user_result, IOSuccess(()))  # list[IOResultE] -> IOResultE[list]


def add_dex_users_via_yaml(
    dex_config: DexAdminConfig,
    yaml_file: Path,
    clean: bool,
    overwrite: bool,
) -> IOResultE[list[str]]:
    """Adds new lomas users to Dex from a YAML file.

    Args:
        dex_config (DexAdminConfig): A DexAdminConfig
        yaml_file (Path | BytesIO): File name to load the users from
        clean (bool): Whether to remove existing users and start with a clean state.
        overwrite(bool): Whether to overwrite existing users.
    """
    # process substitution pipes don't like being resolved...
    # although zsh =(...) solve the issue it won't help <(...)
    user_file = yaml_file if yaml_file.is_absolute() else yaml_file.resolve()
    user_list = UserCollection(**yaml.safe_load(user_file.open(encoding="utf-8")))
    return add_dex_users(dex_config, user_list, clean, overwrite)


@impure_safe
def set_dex_user_password(dex_config: DexAdminConfig, user_name: str, new_password: str) -> bool:
    """Sets the new user password to the Dex user.

    Args:
        dex_config (DexAdminConfig): The dex admin config.
        user_name (str): The user name for which to change the password.
        new_password (str): The new password to set.

    Raises:
        InvalidDexOperation: If the user does not exist.
        grpc.RpcError: If any of the calls to dex fails
    """
    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)
        dex_users = stub.ListPasswords(ListPasswordReq()).passwords

        for dex_user in dex_users:
            if dex_user.username == user_name:
                response = stub.UpdatePassword(
                    UpdatePasswordReq(
                        email=dex_user.email, new_hash=hash_pwd(new_password), new_username=user_name
                    )
                )
                logger.debug(f"Updated password for user {to_log(user_name)}.")
                return not response.not_found

        raise InvalidDexOperation(
            f"Failed to update user password for {to_log(user_name)}. User does not exist."
        )

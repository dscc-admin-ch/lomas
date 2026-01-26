import uuid
from pathlib import Path

import bcrypt
import grpc
import yaml

from lomas_core.models.collections import UserCollection
from lomas_core.models.constants import init_logging
from lomas_server.administration.dex.api.api_pb2 import (
    CreatePasswordReq,
    DeletePasswordReq,
    ListPasswordReq,
    Password,
)
from lomas_server.administration.dex.api.api_pb2_grpc import DexStub
from lomas_server.models.config import DexAdminConfig

logger = init_logging(__name__)


def get_grpc_channel(dex_config: DexAdminConfig) -> grpc.Channel:
    """Returns a valid grpc channel to use as context.

    Note: does not support mTLS yet.

    Args:
        dex_config (DexAdminConfig): The Dex config

    Returns:
        grpc.Channel: A valid grpc channel.
    """
    assert dex_config.use_mtls is False
    return grpc.insecure_channel(str(dex_config.url))


def hash_pwd(password: str) -> bytes:
    """Hashes the password string.

    Args:
        password (str): The password string to hash.

    Returns:
        bytes: The password hash.
    """
    bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes, salt)

    return hash


def add_dex_user(dex_config: DexAdminConfig, user_name: str, user_email: str, user_password: str) -> None:
    """Adds a new user to dex.

    Args:
        dex_config (DexAdminConfig): The DexAdminConfig
        user_name (str): The user name
        user_email (str): The user email
        user_password (str): The user pasword
    """
    new_pwd = Password(
        email=user_email, hash=hash_pwd(user_password), username=user_name, user_id=str(uuid.uuid4())
    )

    try:
        with get_grpc_channel(dex_config) as channel:
            stub = DexStub(channel)
            # TODO check if already exists!
            stub.CreatePassword(CreatePasswordReq(password=new_pwd))
            logger.info(f"Added {user_name} user.")
    except grpc.RpcError as e:
        logger.error(
            f"Could not add user to Dex. Please contact the service administrator.\n Exception: {e!s}"
        )
        raise e

    log_name = user_name.replace("\\r\\n", "").replace("\\n", "")
    logger.info(f"Added dex user {log_name}")


def del_dex_user(dex_config: DexAdminConfig, user_name: str) -> None:
    """Removes the dex user.

    Args:
        dex_config (DexAdminConfig): The DexAdminConfig
        user_name (str): The name of the user to remove.
    """
    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)

        try:
            users = stub.ListPasswords(ListPasswordReq())
        except grpc.RpcError as e:
            logger.error(f"Failed to get list of current Dex users.\n Exception: {e!s}")
            raise e

        for user in users.passwords:
            if user.username == user_name:
                try:
                    # assuming there's a DeletePassword method in DexStub
                    stub.DeletePassword(DeletePasswordReq(email=user.email))
                    logger.info(f"Deleted dex user {user_name}")
                    return
                except grpc.RpcError as e:
                    logger.error(f"Failed to delete user {user_name}.\n Exception: {e!s}")
                    raise e

            logger.error(f"User {user_name} does not exist.")
            raise Exception(f"Cannot delete. User does not exist {user_name}")


def del_all_dex_users(dex_config: DexAdminConfig) -> None:
    """Removes all dex users.

    Args:
        dex_config (DexAdminConfig): The DexAdminConfig

    Raises:
        grpc.RpcError: If any of the calls to dex fails
    """
    with get_grpc_channel(dex_config) as channel:
        stub = DexStub(channel)
        try:
            users = stub.ListPasswords(ListPasswordReq())
        except grpc.RpcError as e:
            logger.error(f"Failed to get list of current Dex users.\n Exception: {e!s}")
            raise e

        breakpoint()

        for user in users.passwords:
            try:
                # assuming there's a DeletePassword method in DexStub
                stub.DeletePassword(DeletePasswordReq(email=user.email))
                logger.info(f"Deleted dex user {user.username}")
            except grpc.RpcError as e:
                logger.error(f"Failed to delete user {user.username}.\n Exception: {e!s}")
                raise e

    logger.info("Removed all dex users.")


def add_dex_users(
    dex_config: DexAdminConfig,
    user_list: UserCollection,
    clean: bool,
    overwrite: bool,
) -> None:
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
        grpc.RpcError: If any of the calls to dex fails
    """
    # Remove all existing users if requested
    if clean:
        del_all_dex_users(dex_config)

    for user in user_list.users:
        # Remove user with same name if requested (but not already cleaned)
        if overwrite and not clean:
            try:
                with get_grpc_channel(dex_config) as channel:
                    stub = DexStub(channel)
                    dex_users = stub.ListPasswords(ListPasswordReq())
            except grpc.RpcError as e:
                logger.error(f"Failed to get Dex users.\n Exception: {e!s}")
                raise e

            for dex_user in dex_users.passwords:
                if dex_user.username == user.id.name:
                    try:
                        stub.DeletePassword(DeletePasswordReq(email=dex_user.email))
                        logger.info(f"Removed existing dex user {user.id.name} due to overwrite flag")
                    except grpc.RpcError as e:
                        logger.error(f"Failed to delete existing dex user {user.id.name}.\n Exception: {e!s}")
                        raise e

        # Create the dex user
        # TODO replace client_secret with password
        if user.id.client_secret is None:
            logger.error(f"Cannot add Dex user {user.id.name} without password")
            raise Exception(f"Cannot add Dex user {user.id.name} without password")

        add_dex_user(dex_config, user.id.name, user.id.email, user.id.client_secret)

    logger.info("Added dex users from user collection.")


def add_dex_users_via_yaml(
    dex_config: DexAdminConfig,
    yaml_file: Path,
    clean: bool,
    overwrite: bool,
) -> None:
    """Adds new lomas users to Dex from a YAML file.

    Args:
        dex_config (DexAdminConfig): A DexAdminConfig
        yaml_file (Path): File name to load the users from
        clean (bool): Whether to remove existing users and start with a clean state.
        overwrite(bool): Whether to overwrite existing users.

    Raises:
        grpc.RpcError: If any of the calls to dex fails
    """
    # Load yaml data and insert it
    user_list = UserCollection(**yaml.safe_load(yaml_file.resolve().open()))
    add_dex_users(dex_config, user_list, clean, overwrite)


def test_api():
    with grpc.insecure_channel("localhost:5557") as channel:
        stub = DexStub(channel)
        res = stub.ListPasswords(ListPasswordReq())
        breakpoint()
        print(res)


if __name__ == "__main__":
    # TODO remove, this is just for testing.import uuid
    config = DexAdminConfig(
        url="localhost:4446",
    )

    add_dex_user(config, "dada", "dada@example.com", "pwd")
    add_dex_user(config, "dada", "dada@example2.com", "pwd")
    add_dex_user(config, "dada2", "dada@example2.com", "pwd")

    breakpoint()
    # del_dex_user(config, "dada")
    del_all_dex_users(config)

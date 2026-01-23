import uuid

import bcrypt
import grpc

from lomas_core.models.constants import init_logging
from lomas_server.administration.dex.api.api_pb2 import CreatePasswordReq, ListPasswordReq, Password
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
    """Hashes the password string

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
            stub.CreatePassword(CreatePasswordReq(password=new_pwd))
    except grpc.RpcError as e:
        logger.info(
            f"Could not add user to Dex. Please contact the service administrator.\n Exception: {e!s}"
        )

    log_name = user_name.replace("\\r\\n", "").replace("\\n", "")
    logger.info(f"Added dex user {log_name}")


def del_dex_user(dex_config: DexAdminConfig, user_name: str) -> None:
    """Removes the dex user.

    Args:
        dex_config (DexAdminConfig): The DexAdminConfig
        user_name (str): The name of the user to remove.
    """
    try:
        with get_grpc_channel(dex_config) as channel:
            stub = DexStub(channel)
            stub.ListPasswords(ListPasswordReq())
    except Exception:
        logger.info("failed")


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

    breakpoint()
    add_dex_user(config, "dada", "dada@example.com", "pwd")
    del_dex_user(config, "dada")

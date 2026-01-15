import bcrypt
import grpc
from api_pb2 import CreatePasswordReq, ListPasswordReq, Password
from api_pb2_grpc import DexStub


def test_api():
    with grpc.insecure_channel("localhost:5557") as channel:
        stub = DexStub(channel)
        res = stub.ListPasswords(ListPasswordReq())
        breakpoint()
        print(res)


def hash_pwd(password: str) -> bytes:
    bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes, salt)

    return hash


def add_user():
    new_pwd = Password(
        email="new_user@example.com", hash=hash_pwd("password"), username="new_user", user_id="1234"
    )
    with grpc.insecure_channel("localhost:5557") as channel:
        stub = DexStub(channel)
        res = stub.CreatePassword(CreatePasswordReq(password=new_pwd))
        breakpoint()
        print(res)


if __name__ == "__main__":
    add_user()
    test_api()

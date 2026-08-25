import os
from pathlib import Path

import pytest
from csvw_eo.metadata_structure import TableMetadata
from fastapi.testclient import TestClient
from returns.pipeline import is_successful
from returns.result import ResultE, Success
from streamlit.testing.v1 import AppTest

from lomas_core.models.collections import User, UserId
from lomas_core.models.constants import PrivateDatabaseType
from lomas_core.models.requests import LomasBudgetRequest, LomasRequestModel
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup
from lomas_server.app import get_admin_app
from lomas_server.models.config import Config
from lomas_server.tests.utils import free_pass_env
from lomas_server.utils.query import query_lomas

test_data_folder = (Path(__file__).parent / "../../tests/test_data").resolve()


@pytest.fixture
def demo_setup():
    config = Config()
    config.database.set_bootstrap(config.bootstrap)

    lomas_demo_setup()

    yield True

    config.database.wipe()


@pytest.fixture
def switch_data_dir():
    key = "LOMAS_SERVICE_data_directory"
    prev_data_dir = os.environ.get(key, "")
    # Server graciously allow Datase collection to have relative path to the `data_directory`
    os.environ[key] = str(test_data_folder)
    yield f"{key} -> {test_data_folder}"
    os.environ[key] = prev_data_dir


@pytest.fixture
def dashbord_dir() -> Path:
    return (Path(__file__).parent / "../dashboard").resolve()


@pytest.fixture
def client() -> TestClient:
    # we need to be admin from there on
    user_name = "lomas_admin"
    headers = {"Authorization": f"Bearer {user_name}"}
    with free_pass_env(), TestClient(get_admin_app(Config()), headers=headers) as client:
        yield client


def test_about_page(dashbord_dir: Path) -> None:
    """Test display about.py page."""
    at = AppTest.from_file(f"{dashbord_dir}/about.py").run()

    assert "Welcome!" in at.title[0].value

    assert "Lomas Administration Dashboard" in at.header[0].value

    assert "Key Features" in at.header[1].value
    assert "Resources" in at.header[2].value

    assert "The Lomas Administration Dashboard" in at.markdown[0].value

    assert "**Documentation**: [server documentation]" in at.markdown[-5].value
    assert "**Support**: If you encounter any issues " in at.markdown[-4].value

    assert "Server Status" in at.header[3].value
    assert "localhost:" in at.markdown[-3].value
    assert "Dex is only supported for demo purposes" in at.markdown[-2].value
    assert "User is not logged" in at.markdown[-1].value


def test_admin_page(dashbord_dir: Path, client: TestClient, demo_setup) -> None:
    assert query_lomas("/live", client.get) == Success({"status": "alive"})

    assert query_lomas("/datasets", client.get) == Success(
        ["IRIS", "PENGUIN", "PUMS", "TITANIC", "FSO_INCOME_SYNTHETIC", "COVID_SYNTHETIC", "BIRTHDAYS"]
    )

    users = query_lomas("/users", client.get)
    assert is_successful(users)

    user_name = "Dr.Antartica"
    assert users.map(
        lambda user_list: len([u for u in user_list if u["id"]["name"] == user_name])
    ) == Success(1), f"{user_name} not found in /users"

    budgetReq = LomasBudgetRequest(dataset_name="PUMS", epsilon=0.3, delta=0.005)
    assert is_successful(
        query_lomas(f"/users/{user_name}/dataset/budget", client.patch, json=budgetReq.model_dump())
    )

    assert query_lomas("/dataset/PUMS/metadata", client.get).map(
        lambda meta: len(meta.keys()) > 5
    ) == Success(True)


def test_add_rm_user(client: TestClient, demo_setup) -> None:
    username = "newUser"

    new_user = User(id=UserId(name=username, email="new@user.com"), may_query=True, datasets={})
    assert is_successful(query_lomas("/users", client.post, json=new_user.model_dump()))
    assert query_lomas(f"/users/{username}/archive", client.get) == Success([])
    assert is_successful(query_lomas(f"/users/{username}", client.delete))


def test_add_rm_dataset(client: TestClient, demo_setup) -> None:
    user_name = "Dr.Antartica"
    ds_name = "test_dataset"

    post_dataset = query_lomas(
        "/dataset",
        client.post,
        json={
            "dataset_name": ds_name,
            "database_type": PrivateDatabaseType.PATH,
            "metadata_database_type": PrivateDatabaseType.PATH,
            "dataset_path": str(test_data_folder / "test_penguin.csv"),
            "metadata_path": str(test_data_folder / "metadata" / "penguin_metadata.json"),
        },
    )
    assert is_successful(post_dataset)

    # Ensure dataset is present
    assert query_lomas(f"/dataset/{ds_name}", client.get).map(
        lambda res: res.get("dataset_name") == ds_name
    ) == Success(True)

    assert is_successful(
        query_lomas(
            f"/users/{user_name}/dataset",
            client.patch,
            json=LomasRequestModel(dataset_name=ds_name).model_dump(),
        )
    )
    # Ensure <user> has the new dataset in their list
    assert query_lomas("/users", client.get).map(
        lambda user_list: next(u["datasets"] for u in user_list if u["id"]["name"] == user_name)
    ).map(lambda ds_dict: ds_name in ds_dict) == Success(1)

    assert is_successful(query_lomas(f"/dataset/{ds_name}", client.delete))
    # Ensure dataset deletion
    assert not is_successful(query_lomas(f"/dataset/{ds_name}", client.get))

    assert is_successful(
        query_lomas(
            f"/users/{user_name}/dataset/del",
            client.patch,
            json=LomasRequestModel(dataset_name=ds_name).model_dump(),
        )
    )
    # Ensure <user> no longer has the new dataset in their list
    assert query_lomas("/users", client.get).map(
        lambda user_list: next(u["datasets"] for u in user_list if u["id"]["name"] == user_name)
    ).map(lambda ds_dict: ds_name in ds_dict) == Success(0)


def test_add_user_yaml(client: TestClient, demo_setup) -> None:
    user_collection_file = test_data_folder / "test_user_collection.yaml"

    query_result = query_lomas(
        "/usersfile",
        client.post,
        data={"clean": False, "overwrite": True},  # , "overwrite": False},
        files={"file": user_collection_file.open(mode="rb")},
    )

    assert is_successful(query_result)


def test_add_dataset_yaml(client: TestClient, demo_setup, switch_data_dir) -> None:
    dataset_collection = test_data_folder / "test_datasets.yaml"
    post_result = query_lomas(
        "/dataset/bulk",
        client.post,
        data={"clean": True},
        files={"file": dataset_collection.open(mode="rb")},
    )
    assert is_successful(post_result)

    ds_name = "PUMS"
    old_metadata: ResultE[TableMetadata] = query_lomas(f"/dataset/{ds_name}/metadata", client.get)
    assert is_successful(old_metadata)
    validated = old_metadata.map(TableMetadata.model_validate)
    assert is_successful(validated)

    # override pums with penguin metadatas
    penguin_metadata = test_data_folder / "metadata" / "penguin_metadata.json"
    patch_result = query_lomas(
        f"/dataset/{ds_name}/metadata", client.patch, files={"file": penguin_metadata.open(mode="rb")}
    )
    assert is_successful(patch_result)

    new_metadata = query_lomas(f"/dataset/{ds_name}/metadata", client.get)
    assert is_successful(new_metadata)

    assert old_metadata != new_metadata
    assert old_metadata.map(lambda meta: [col["name"] for col in meta["columns"]]) != new_metadata.map(
        lambda meta: [col["name"] for col in meta["columns"]]
    )

import pytest
import os
from unittest.mock import patch, MagicMock
from streamlit.testing.v1 import AppTest
from lomas_core.models.constants import (
    PrivateDatabaseType,
)
from io import BytesIO
import mongomock


def get_mocked_db():
    client = mongomock.MongoClient()
    db = client["test_db"]
    return db


def load_mock_file(file_path: str) -> BytesIO:
    """
    Loads the YAML content from a given file path and returns a mock BytesIO file-like object.
    """
    with open(file_path, "rb") as file:
        mock_file = BytesIO(file.read())
        mock_file.name = os.path.basename(file_path)
    return mock_file


@pytest.fixture
def mock_mongodb_and_helpers():
    """Fixture to mock the MongoDB and helper functions used in the Streamlit app."""
    with patch(
        "lomas_server.admin_database.utils.get_mongodb"
    ) as mock_get_mongodb, patch("streamlit.file_uploader") as mock_file_uploader:

        mock_get_mongodb.return_value = get_mocked_db()
        mock_file_path = "../data/collections/metadata/iris_metadata.yaml"
        mock_file = load_mock_file(mock_file_path)
        mock_file_uploader.return_value = mock_file
        # Yield the mocks to the tests
        yield {
            "mock_get_mongodb": mock_get_mongodb,
            "mock_file_uploader": mock_file_uploader,
        }


def test_dataset_tab(mock_mongodb_and_helpers):
    """Test adding a dataset via the admin dashboard."""
    # Simulate interaction with the Streamlit app

    at = AppTest.from_file("../dashboard/pages/b_database_administration.py").run()

    ## Dataset tab
    ### Add dataset (working), PATH/PATH
    at.text_input("ad_dataset").set_value("IRIS").run()
    at.selectbox("ad_type").set_value(PrivateDatabaseType.PATH).run()
    at.selectbox("ad_meta_type").set_value(PrivateDatabaseType.PATH).run()
    at.text_input("ad_path").set_value(
        "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"
    ).run()
    at.button("add_dataset_with_metadata").click().run()
    assert at.success[0].value == "File iris_metadata.yaml uploaded successfully!"
    assert at.markdown[0].value == "Dataset IRIS was added."
    assert at.session_state["list_datasets"] == ["IRIS"]


def test_user_tab(mock_mongodb_and_helpers):
    """Test adding a user via the admin dashboard."""

    # Simulate interaction with the Streamlit app
    at = AppTest.from_file("../dashboard/pages/b_database_administration.py").run()

    ## User tab
    ### Subheader "Add user"
    at.text_input("au_username_key").set_value("").run()
    at.button("add_user_button").click().run()
    assert at.warning[0].value == "Please fill all fields."

    at.text_input("au_username_key").set_value("test").run()
    at.button("add_user_button").click().run()
    assert at.markdown[0].value == "User test was added."

    at.text_input("au_username_key").set_value("test").run()
    at.button("add_user_button").click().run()
    assert at.warning[0].value == "User test is already in the database."

    ### Subheader "Add user with budget"
    at.text_input("auwb_username").set_value("Bobby").run()
    at.selectbox("dataset of add user with budget").set_value("PENGUIN").run()
    at.number_input("auwb_epsilon").set_value(None).run()
    at.number_input("auwb_delta").set_value(None).run()
    at.button("add_user_with_budget").click().run()
    assert at.warning[0].value == "Please fill all fields."

    # at.text_input("auwb_username").set_value("Bobby").run()
    # at.selectbox("dataset of add user with budget").set_value("PENGUIN").run()
    # at.number_input("auwb_epsilon").set_value(10).run()
    # at.number_input("auwb_delta").set_value(0.5).run()
    # at.button("add_user_with_budget").click().run()
    # assert at.markdown[0].value == "User Bobby was added with dataset PENGUIN."

    # ### Subheader "Add dataset to user"
    # at.selectbox("username of add dataset to user").set_value("Bobby").run()
    # at.selectbox("dataset of add dataset to user").set_value("IRIS").run()
    # at.number_input("adtu_epsilon").set_value(10).run()
    # at.number_input("adtu_delta").set_value(0.5).run()
    # at.button("add_dataset_to_user").click().run()
    # assert at.markdown[0].value == "User Bobby was added with dataset PENGUIN."

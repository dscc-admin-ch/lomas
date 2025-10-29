import json
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from lomas_core.models.constants import PrivateDatabaseType
from lomas_server.models.config import AdminConfig


@pytest.fixture
def mock_and_helpers():
    """Fixture to mock the helper functions used in the Streamlit app."""
    with patch("streamlit.file_uploader") as mock_file_uploader:
        mock_file_path = Path(__file__).parent / "../../../data/collections/metadata/iris_metadata.yaml"
        mock_file = BytesIO(mock_file_path.read_bytes())
        mock_file.name = mock_file_path.name
        mock_file_uploader.return_value = mock_file

        yield mock_file_uploader


@pytest.fixture
def at():
    admin_db = AdminConfig().database
    admin_db.wipe()

    yield AppTest.from_file("../dashboard/pages/b_database_administration.py").run()

    # post-clean by politesse
    admin_db.wipe()


@pytest.fixture
def dataset_iris(at: AppTest, mock_and_helpers):
    at.text_input("ad_dataset").set_value("IRIS").run()
    at.selectbox("ad_type").set_value(PrivateDatabaseType.PATH).run()
    at.selectbox("ad_meta_type").set_value(PrivateDatabaseType.PATH).run()
    at.text_input("ad_path").set_value(
        "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"
    ).run()
    at.button("add_dataset_with_metadata").click().run()
    assert at.success[0].value == "File iris_metadata.yaml uploaded successfully!"
    assert at.markdown[0].value == "Dataset IRIS was added."
    assert at.session_state.list_datasets == ["IRIS"]

    yield

    at.selectbox("rd_dataset").set_value("IRIS").run()
    at.button("delete_dataset_and_metadata").click().run()
    assert at.session_state.list_datasets == []


def test_widgets(at: AppTest, dataset_iris) -> None:
    """Test the different widgets (add/remove users/datasets/metadata)."""
    # User tab
    # Subheader "Add user"
    at.text_input("au_username_key").set_value("").run()
    at.button("add_user_button").click().run()
    assert at.warning[0].value == "Please fill all fields."

    at.text_input("au_username_key").set_value("test").run()
    at.text_input("au_email_key").set_value("test@test.com").run()
    at.button("add_user_button").click().run()
    assert at.markdown[0].value == "User test was added."

    at.text_input("au_username_key").set_value("test").run()
    at.text_input("au_email_key").set_value("test@test.com").run()
    at.button("add_user_button").click().run()
    assert at.warning[0].value == "User test is already in the database."
    # assert at.warning[1].value == "Please fill all fields."

    # Subheader "Add user with budget"
    at.text_input("auwb_username").set_value("Bobby").run()
    at.text_input("auwb_email_key").set_value("bobby@test.com").run()
    at.selectbox("dataset of add user with budget").set_value("IRIS").run()
    at.number_input("auwb_epsilon").set_value(None).run()
    at.number_input("auwb_delta").set_value(None).run()
    at.button("add_user_with_budget").click().run()
    assert at.warning[0].value == "Please fill all fields."

    at.text_input("auwb_username").set_value("Bobby").run()
    at.text_input("auwb_email_key").set_value("bobby@test.com").run()
    at.selectbox("dataset of add user with budget").set_value("IRIS").run()
    at.number_input("auwb_epsilon").set_value(10).run()
    at.number_input("auwb_delta").set_value(0.01).run()
    at.button("add_user_with_budget").click().run()
    assert at.markdown[0].value == "User Bobby was added with dataset IRIS."

    # Subheader "Add dataset to user"
    at.selectbox("username of add dataset to user").set_value("test").run()
    at.selectbox("dataset of add dataset to user").set_value("IRIS").run()
    at.number_input("adtu_epsilon").set_value(10).run()
    at.number_input("adtu_delta").set_value(0.01).run()
    at.button("add_dataset_to_user").click().run()
    assert at.markdown[0].value == "Dataset IRIS was added to user test with epsilon = 10.0 and delta = 0.01"

    # Subheader "Modify user epsilon"
    at.selectbox("username of modify user epsilon").set_value("test").run()
    at.selectbox("dataset of modify user epsilon").set_value("IRIS").run()
    at.number_input("sue_epsilon").set_value(1).run()
    at.button("modify_user_epsilon").click().run()
    assert at.markdown[0].value == "User test on dataset IRIS initial epsilon value was modified to 1.0"

    # Subheader "Modify user delta"
    at.selectbox("username of modify user delta").set_value("test").run()
    at.selectbox("dataset of modify user delta").set_value("IRIS").run()
    at.number_input("sud_delta").set_value(0.001).run()
    at.button("modify_user_delta").click().run()
    assert at.markdown[0].value == "User test on dataset IRIS initial delta value was modified to 0.001"

    # Subheader "Modify user may query"
    at.selectbox("username of user may query").set_value("test").run()
    at.selectbox("umq_may_query").set_value(False).run()
    at.button("m_u_m_q").click().run()
    assert at.markdown[0].value == "User test may_query is now: `False`"

    # Content tab
    # Subheader "Show one element"
    at.selectbox("username of user to show").set_value("test").run()
    at.button("content_user_display").click().run()
    result = json.loads(at.json[0].value)
    assert result["id"]["name"] == "test"
    assert not result["may_query"]

    at.selectbox("username of archives from user").set_value("test").run()
    at.button("content_user_archive_display").click().run()
    assert json.loads(at.json[0].value) == []

    at.selectbox("dataset_to_show").set_value("IRIS").run()
    at.button("content_dataset_display").click().run()
    result = json.loads(at.json[0].value)
    assert result["dataset_name"] == "IRIS"
    assert "dataset_access" in result

    at.selectbox("metadata_of_dataset_to_show").set_value("IRIS").run()
    at.button("content_metadata_dataset_display").click().run()
    result = json.loads(at.json[0].value)
    assert result["max_ids"] == 1
    assert result["rows"] == 150

    # Subheader "Show full collection"
    at.button("content_show_all_users").click().run()
    assert json.loads(at.json[0].value)["test"]["id"]["name"] == "test"

    at.button("content_show_all_datasets").click().run()
    assert json.loads(at.json[0].value)[0]["dataset_name"] == "IRIS"

    at.button("content_show_all_metadata").click().run()
    assert json.loads(at.json[0].value)["IRIS"]["max_ids"] == 1

    at.button("content_show_archives").click().run()
    # assert json.loads(at.json[0].value) == []

    # Deletion tab
    # Subheader "Delete one element"
    # Remove dataset from user
    at.selectbox("rdtu_user").set_value("test").run()
    at.selectbox("rdtu_dataset").set_value("IRIS").run()
    at.button("delete_dataset_from_user").click().run()
    assert at.markdown[3].value == "Dataset IRIS was removed from user test."

    # Delete one user
    at.selectbox("du_username").set_value("test").run()
    at.button("delete_user").click().run()
    assert at.session_state["list_users"] == ["Bobby"]
    assert at.markdown[2].value == "User test was deleted."

    # Subheader "Delete full collection"
    at.button("delete_all_users").click().run()
    assert at.markdown[4].value == "Users were all deleted."

    at.button("delete_all_datasets").click().run()
    assert at.markdown[4].value == "Datasets were all deleted."

    at.button("delete_all_metadata").click().run()
    assert at.markdown[4].value == "Metadata were all deleted."

    at.button("delete_all_archives").click().run()
    assert at.markdown[4].value == "Archives were all deleted."


def test_layout(at: AppTest) -> None:
    """Test the layout of administration page b."""
    # Check the title
    assert "Admin Database Management" in at.title[0].value

    # Check tab "user management"
    assert at.tabs[0].label == ":technologist: User Management"
    assert "Add user" in at.subheader[0].value
    assert "Add user with budget" in at.subheader[1].value
    assert "Add dataset to user" in at.subheader[2].value
    assert "Set user client secret" in at.subheader[3].value
    assert "Modify user epsilon" in at.subheader[4].value
    assert "Modify user delta" in at.subheader[5].value
    assert "Modify user may query" in at.subheader[6].value
    assert "Add many users via a yaml file" in at.subheader[7].value

    # Check tab "user management"
    assert at.tabs[1].label == ":file_cabinet: Dataset Management"
    assert "Add one dataset" in at.subheader[8].value
    assert "Add many datasets via a yaml file" in at.subheader[9].value

    # Check tab "view database content"
    assert at.tabs[2].label == ":eyes: View Database Content"
    assert "Show one element" in at.subheader[10].value
    assert "Show full collection" in at.subheader[11].value

    # Check tab "delete content"
    assert at.tabs[3].label == ":wastebasket: Delete Content (:red[DANGEROUS])"
    assert at.markdown[0].value == ":warning: :red[**Danger Zone: deleting is final**]"

    assert "Delete one element" in at.subheader[12].value
    assert at.markdown[1].value == "**Delete one user**"
    assert at.markdown[2].value == "**Remove dataset from user**"
    assert at.markdown[3].value == "**Remove dataset and it's associated metadata**"

    assert "Delete full collection" in at.subheader[13].value

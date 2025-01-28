from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from lomas_core.models.constants import (
    PrivateDatabaseType,
)
from lomas_server.administration.tests.utils import get_mocked_db, load_mock_file


@pytest.fixture
def mock_mongodb_and_helpers():
    """Fixture to mock the MongoDB and helper functions used in the Streamlit app."""
    with patch("lomas_server.admin_database.utils.get_mongodb") as mock_get_mongodb, patch(
        "streamlit.file_uploader"
    ) as mock_file_uploader:

        mock_get_mongodb.return_value = get_mocked_db()
        mock_file_path = "../data/collections/metadata/iris_metadata.yaml"
        mock_file = load_mock_file(mock_file_path)
        mock_file_uploader.return_value = mock_file
        # Yield the mocks to the tests
        yield {
            "mock_get_mongodb": mock_get_mongodb,
            "mock_file_uploader": mock_file_uploader,
        }


def test_widgets(mock_mongodb_and_helpers):  # pylint: disable=W0621, W0613, R0915
    """Test the different widgets (add/remove users/datasets/metadata)."""

    # Simulate interaction with the Streamlit app
    at = AppTest.from_file("../dashboard/pages/b_database_administration.py").run()

    # Dataset tab
    # Add dataset (working), PATH/PATH
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

    # TODO 374: Add tests for upload_file widgets

    # User tab
    # Subheader "Add user"
    at.text_input("au_username_key").set_value("").run()
    at.button("add_user_button").click().run()
    assert at.warning[0].value == "Please fill all fields."

    at.text_input("au_username_key").set_value("test").run()
    at.button("add_user_button").click().run()
    assert at.markdown[0].value == "User test was added."

    at.text_input("au_username_key").set_value("test").run()
    at.button("add_user_button").click().run()
    assert at.warning[0].value == "User test is already in the database."

    # Subheader "Add user with budget"
    at.text_input("auwb_username").set_value("Bobby").run()
    at.selectbox("dataset of add user with budget").set_value("IRIS").run()
    at.number_input("auwb_epsilon").set_value(None).run()
    at.number_input("auwb_delta").set_value(None).run()
    at.button("add_user_with_budget").click().run()
    assert at.warning[0].value == "Please fill all fields."

    at.text_input("auwb_username").set_value("Bobby").run()
    at.selectbox("dataset of add user with budget").set_value("IRIS").run()
    at.number_input("auwb_epsilon").set_value(10).run()
    at.number_input("auwb_delta").set_value(0.5).run()
    at.button("add_user_with_budget").click().run()
    assert at.markdown[0].value == "User Bobby was added with dataset IRIS."

    # Subheader "Add dataset to user"
    at.selectbox("username of add dataset to user").set_value("test").run()
    at.selectbox("dataset of add dataset to user").set_value("IRIS").run()
    at.number_input("adtu_epsilon").set_value(10).run()
    at.number_input("adtu_delta").set_value(0.5).run()
    at.button("add_dataset_to_user").click().run()
    assert at.markdown[0].value == "Dataset IRIS was added to user test with epsilon = 10.0 and delta = 0.5"

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
    assert (at.json[0].value.startswith('{"user_name": "test", "may_query": false')) is True

    at.selectbox("username of archives from user").set_value("test").run()
    at.button("content_user_archive_display").click().run()
    assert at.json[0].value == "[]"

    at.selectbox("dataset_to_show").set_value("IRIS").run()
    at.button("content_dataset_display").click().run()
    assert (at.json[0].value.startswith('{"dataset_name": "IRIS", "dataset_access"')) is True

    at.selectbox("metadata_of_dataset_to_show").set_value("IRIS").run()
    at.button("content_metadata_dataset_display").click().run()
    assert at.json[0].value.startswith('{"max_ids": 1, "rows": 150') is True

    # Subheader "Show full collection"
    at.button("content_show_all_users").click().run()
    assert at.json[0].value.startswith('[{"user_name": "test"') is True

    at.button("content_show_all_datasets").click().run()
    assert at.json[0].value.startswith('[{"dataset_name": "IRIS"') is True

    at.button("content_show_all_metadata").click().run()
    assert at.json[0].value.startswith('[{"IRIS": {"max_ids": 1') is True

    at.button("content_show_archives").click().run()
    assert at.json[0].value.startswith("[]") is True

    # Deletion tab
    # Subheader "Delete one element"
    # Remove dataset from user
    at.selectbox("rdtu_user").set_value("test").run()
    at.selectbox("rdtu_dataset").set_value("IRIS").run()
    at.button("delete_dataset_from_user").click().run()
    assert at.markdown[3].value == "Dataset IRIS was removed from user test."

    # Remove dataset and it's associated metadata
    at.selectbox("rd_dataset").set_value("IRIS").run()
    at.button("delete_dataset_and_metadata").click().run()
    assert at.session_state["list_datasets"] == []
    assert at.markdown[4].value == "Dataset IRIS was deleted."

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


def test_layout(mock_mongodb_and_helpers):  # pylint: disable=W0621, W0613
    """Test the layout of administration page b."""

    # Simulate interaction with the Streamlit app
    at = AppTest.from_file("../dashboard/pages/b_database_administration.py").run()

    # Check the title
    assert "Admin Database Management" in at.title[0].value

    # Check tab "user management"
    assert at.tabs[0].label == ":technologist: User Management"
    assert "Add user" in at.subheader[0].value
    assert "Add user with budget" in at.subheader[1].value
    assert "Add dataset to user" in at.subheader[2].value
    assert "Modify user epsilon" in at.subheader[3].value
    assert "Modify user delta" in at.subheader[4].value
    assert "Modify user may query" in at.subheader[5].value
    assert "Add many users via a yaml file" in at.subheader[6].value

    # Check tab "user management"
    assert at.tabs[1].label == ":file_cabinet: Dataset Management"
    assert "Add one dataset" in at.subheader[7].value
    assert "Add many datasets via a yaml file" in at.subheader[8].value

    # Check tab "view database content"
    assert at.tabs[2].label == ":eyes: View Database Content"
    assert "Show one element" in at.subheader[9].value
    assert "Show full collection" in at.subheader[10].value

    # Check tab "delete content"
    assert at.tabs[3].label == ":wastebasket: Delete Content (:red[DANGEROUS])"
    assert at.markdown[0].value == ":warning: :red[**Danger Zone: deleting is final**] :warning:"

    assert "Delete one element" in at.subheader[11].value
    assert at.markdown[1].value == "**Delete one user**"
    assert at.markdown[2].value == "**Remove dataset from user**"
    assert at.markdown[3].value == "**Remove dataset and it's associated metadata**"

    assert "Delete full collection" in at.subheader[12].value

import pytest
from unittest.mock import patch, MagicMock
from streamlit.testing.v1 import AppTest
from lomas_core.models.constants import (
    AdminDBType,
    PrivateDatabaseType,
    TimeAttackMethod,
)
from io import BytesIO
import mongomock
from pymongo import MongoClient

from lomas_core.models.config import MongoDBConfig
from pymongo import MongoClient
from lomas_server.utils.config import CONFIG_LOADER, get_config

from lomas_server.admin_database.utils import (
    add_demo_data_to_mongodb_admin,
    get_mongodb_url,
)
from lomas_server.mongodb_admin import (
    add_dataset,
    add_dataset_to_user,
    add_datasets_via_yaml,
    add_user,
    add_user_with_budget,
    add_users_via_yaml,
    del_dataset,
    del_dataset_to_user,
    del_user,
    drop_collection,
    get_archives_of_user,
    get_collection,
    get_dataset,
    get_list_of_datasets,
    get_list_of_datasets_from_user,
    get_list_of_users,
    get_metadata_of_dataset,
    get_user,
    set_budget_field,
    set_may_query,
)
from lomas_server.utils.config import CONFIG_LOADER
# Mock functions used in the Streamlit app
from lomas_server.admin_database.utils import get_mongodb
from lomas_server.mongodb_admin import get_list_of_users, add_user, add_user_with_budget, get_list_of_datasets
from lomas_server.administration.dashboard.utils import check_user_warning, warning_field_missing
from lomas_core.models.config import MongoDBConfig

def get_mocked_db():
    client = mongomock.MongoClient()
    db = client["test_db"]  # Replace 'test_db' with your database name
    return db

class mock_path:
    def __init__(self, name):
        self.name = name

@pytest.fixture
def mock_mongodb_and_helpers():
    """Fixture to mock the MongoDB and helper functions used in the Streamlit app."""
    with patch("lomas_server.admin_database.utils.get_mongodb") as mock_get_mongodb, patch(
        "streamlit.file_uploader") as mock_file_uploader:
        
        mock_get_mongodb.return_value = get_mocked_db()
        
        # Create a mocked file object
        
        mock_file = BytesIO(b"fake file content")
        mock_file.name = "test_file.yaml"
        mock_file_uploader.return_value = mock_file
        # Yield the mocks to the tests
        yield {
            "mock_get_mongodb": mock_get_mongodb,
            "mock_file_uploader":mock_file_uploader,
        }

def test_dataset_tab(mock_mongodb_and_helpers):
    """Test adding a dataset via the admin dashboard."""
    # Simulate interaction with the Streamlit app
    
    at = AppTest.from_file("../dashboard/pages/b_database_administration.py").run()
    
    ## Dataset tab
    ### Subheader "Add user"
    at.text_input("ad_dataset").set_value("IRIS").run()
    at.selectbox("ad_type").set_value(PrivateDatabaseType.PATH).run()
    at.selectbox("ad_meta_type").set_value(PrivateDatabaseType.PATH).run()
    at.text_input("ad_path").set_value("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv").run()
    # Interact with the file_uploader widget
    at.button("add_dataset_with_metadata").click().run()
    assert at.markdown[0].value == "Dataset IRIS was added."

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
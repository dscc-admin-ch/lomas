import pytest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from lomas_core.models.constants import (
    AdminDBType,
    PrivateDatabaseType,
    TimeAttackMethod,
)

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

@pytest.fixture
def mock_mongodb_and_helpers():
    """Fixture to mock the MongoDB and helper functions used in the Streamlit app."""
    with patch("lomas_server.admin_database.utils.get_mongodb") as mock_get_mongodb:
        
        CONFIG_LOADER.load_config(
            config_path="tests/test_configs/test_config_mongo.yaml",
            secrets_path="tests/test_configs/test_secrets.yaml",
        )

        # Access to MongoDB
        admin_config = get_config().admin_database
        if isinstance(admin_config, MongoDBConfig):
            mongo_config: MongoDBConfig = admin_config
        else:
            raise TypeError("Loaded config does not contain a MongoDBConfig.")

        db_url = get_mongodb_url(mongo_config)
        db = MongoClient(db_url)[mongo_config.db_name]
        
        # Mock the return values for MongoDB and helpers
        mock_get_mongodb.return_value = db
        
        # Yield the mocks to the tests
        yield {
            "mock_get_mongodb": mock_get_mongodb,
        }


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
    
    at.text_input("au_username_key").set_value("Alice").run()
    at.button("add_user_button").click().run()
    assert at.warning[0].value == "User Alice is already in the database."
    
    ### Subheader "Add user with budget"
    at.text_input("auwb_username").set_value("Bobby").run()
    at.selectbox("dataset of add user with budget").set_value("PENGUIN").run()
    at.number_input("auwb_epsilon").set_value(None).run()
    at.number_input("auwb_delta").set_value(None).run()
    at.button("add_user_with_budget").click().run()
    assert at.warning[0].value == "Please fill all fields."
    
    at.number_input("auwb_epsilon").set_value(10).run()
    at.number_input("auwb_delta").set_value(0.5).run()
    at.button("add_user_with_budget").click().run()
    assert at.markdown[0].value == "User Bobby was added with dataset PENGUIN."
    
    ### Subheader "Add dataset to user"
    at.selectbox("username of add dataset to user").set_value("Bobby").run()
    at.selectbox("dataset of add dataset to user").set_value("IRIS").run()
    at.number_input("adtu_epsilon").set_value(10).run()
    at.number_input("adtu_delta").set_value(0.5).run()
    at.button("add_dataset_to_user").click().run()
    
    assert at.markdown[0].value == "User Bobby was added with dataset PENGUIN."
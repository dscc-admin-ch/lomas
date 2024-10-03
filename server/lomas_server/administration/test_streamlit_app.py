from streamlit.testing.v1 import AppTest
from unittest.mock import patch
import pytest
from lomas_server.administration.dashboard.config import Config


def test_about_page():
    """Test display about.py page"""
    at = AppTest.from_file("dashboard/about.py").run()

    # Check the title
    assert "Welcome!" in at.title[0].value
    
    # Check the main header
    assert "Lomas Administation Dashboard" in at.header[0].value
    
    # Check the sub-header or other headers
    assert "Key Features" in at.header[1].value
    assert "Quick Start" in at.header[2].value
    assert "Resources" in at.header[3].value

    # Check the body text
    assert "The Lomas Administration Dashboard" in at.markdown[0].value

    # Check resources section
    assert "**Documentation**: [server documentation]" in at.markdown[-2].value
    assert "**Support**: If you encounter any issues " in at.markdown[-1].value


@pytest.fixture
def mock_configs():
    with patch("lomas_server.administration.dashboard.config.get_config") as mock_get_config, \
         patch("lomas_server.utils.config.get_config") as mock_get_server_config:
        # Mock return values for the configurations
        config = {
            "server_url": "example.com",
            "server_service": "http://localhost:8000"
        }
        mock_get_config.return_value = Config.model_validate(config)

        mock_get_server_config.return_value = {
            "server": {
                "host_ip": "192.168.1.1",
                "host_port": 8080,
                "time_attack": {"method": "jitter"}
            },
            "admin_database": {
                "db_type": "YAML",
                "db_file": "database.yml"
            },
            "develop_mode": False
        }
        
        yield


def test_01_server_overview_page(mock_configs):
    """Test display 01_server_overview.py page"""
    at = AppTest.from_file("dashboard/pages/01_server_overview.py").run()

    # Check the title
    assert "Lomas configurations" in at.title[0].value
    
    # Check server URL
    assert "The server is available for requests at the address:" in at.markdown[0].value
    assert "https://example.com" in at.markdown[0].value

    # # Server state messages
    # # Assuming the mocked state response indicates the server is live
    # assert "The server is live and ready!" in at.markdown[1].value

    # # Development mode
    # assert ":red[The server is in PRODUCTION mode.]" in at.markdown[2].value

    # # Check Server configurations
    # assert "Server configurations" in at.subheader[0].value
    # assert "The host IP of the server is: 192.168.1.1" in at.markdown[3].value
    # assert "The host port of the server is : 8080" in at.markdown[4].value
    # assert "The method against timing attack is: hash" in at.markdown[5].value

    # # Check Administration Database information
    # assert "Administration Database" in at.subheader[1].value
    # assert "The administration database type is: YAML" in at.markdown[6].value
    # assert "The database file is: database.yml" in at.markdown[7].value

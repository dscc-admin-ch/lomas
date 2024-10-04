from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from lomas_server.administration.dashboard.config import Config as DashboardConfig
from lomas_server.utils.config import CONFIG_LOADER


def test_about_page():
    """Test display about.py page."""
    at = AppTest.from_file("../dashboard/about.py").run()

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
    """Fixture to mock server and dashboard configs."""
    with patch(
        "lomas_server.administration.dashboard.config.get_config"
    ) as mock_get_config, patch(
        "lomas_server.administration.dashboard.utils.get_server_data"
    ) as mock_get_server_data:

        # Overwrite server config
        CONFIG_LOADER.load_config(
            config_path="tests/test_configs/test_config.yaml",
            secrets_path="tests/test_configs/test_secrets.yaml",
        )

        # Mock dashboard config
        dashboard_config = {
            "server_url": "example.com",
            "server_service": "http://localhost:8000",
        }
        mock_get_config.return_value = DashboardConfig.model_validate(dashboard_config)

        # Mock get server data request
        mock_get_server_data.return_value = {
            "state": {"LIVE": True, "message": "Server is live"}
        }

        yield


def test_a_server_overview_page(mock_configs):  # pylint: disable=W0621, W0613
    """Test display a_server_overview.py page."""

    at = AppTest.from_file("../dashboard/pages/a_server_overview.py").run()

    # Check the title
    assert "Lomas configurations" in at.title[0].value

    # Check server URL
    assert (
        "The server is available for requests at the address:" in at.markdown[0].value
    )
    assert "https://example.com" in at.markdown[0].value

    # Server state messages
    assert "The server is live and ready!" in at.markdown[1].value
    assert ":red[The server is in DEVELOPMENT mode.]" in at.markdown[2].value

    # Check Server configurations
    assert "Server configurations" in at.subheader[0].value
    assert "The host IP of the server is: 0.0.0.0" in at.markdown[3].value
    assert "The method against timing attack is: stall" in at.markdown[5].value

    # Check Administration Database information
    assert "Administration Database" in at.subheader[1].value
    assert "The administration database type is: yaml" in at.markdown[6].value
    assert (
        "The database file is: tests/test_data/local_db_file.yaml"
        in at.markdown[7].value
    )


def test_b_database_administration_page(mock_configs):  # pylint: disable=W0621, W0613
    """Test display b_database_administration.py page."""

    # TODO 353
    # at = AppTest.from_file("../dashboard/pages/b_database_administration.py").run()

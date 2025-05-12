from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from lomas_core.models.config import AdminConfig, Config


def test_about_page() -> None:
    """Test display about.py page."""
    admin_dir = Path(__file__).parent.parent
    at = AppTest.from_file(f"{admin_dir}/dashboard/about.py").run()

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
    with (
        patch("lomas_core.models.config.AdminConfig") as mock_get_config,
        patch("lomas_server.administration.dashboard.utils.get_server_data") as mock_get_server_data,
        patch("lomas_server.administration.dashboard.utils.get_server_config") as mock_get_server_config,
    ):
        # Mock server config
        mock_get_server_config.return_value = Config()

        # Mock dashboard config
        dashboard_config = {
            "mg_config": AdminConfig(kc_config=None).mg_config,
            "kc_config": None,
            "server_url": "https://example.com",
            "server_service": "http://localhost:8000",
        }
        mock_get_config.return_value = AdminConfig(**dashboard_config)

        # Mock get server data request
        mock_get_server_data.return_value = {"state": "live"}

        yield


def test_a_server_overview_page(mock_configs) -> None:  # pylint: disable=W0621, W0613
    """Test display a_server_overview.py page."""

    admin_dir = Path(__file__).parent.parent
    at = AppTest.from_file(f"{admin_dir}/dashboard/pages/a_server_overview.py").run()

    # Check the title
    assert "Lomas configurations" in at.title[0].value

    # Check server URL
    assert "The server is available for requests at the address:" in at.markdown[0].value
    assert "https://example.com" in at.markdown[0].value

    # Server state messages
    assert "The server is live and ready!" in at.markdown[1].value
    assert ":red[The server is in PRODUCTION mode.]" in at.markdown[2].value

    # Check Server configurations
    assert "Server configurations" in at.subheader[0].value
    assert "The host IP of the server is: 0.0.0.0" in at.markdown[3].value
    assert "The method against timing attack is: jitter" in at.markdown[5].value

    # Check Administration Database information
    assert "Administration Database" in at.subheader[1].value
    assert "Its address is:  localhost" in at.markdown[6].value
    assert "Its port is:  `27017`" in at.markdown[7].value
    assert "Its username is:  user" in at.markdown[8].value
    assert "Its database name is:  defaultdb" in at.markdown[9].value

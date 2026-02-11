from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


@pytest.fixture
def dashbord_dir() -> Path:
    return Path(__file__).parent / "../dashboard"


@pytest.mark.skip("Ongoing changes...")
def test_about_page(dashbord_dir: Path) -> None:
    """Test display about.py page."""
    at = AppTest.from_file(f"{dashbord_dir}/about.py").run()

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


@pytest.mark.skip("Ongoing changes...")
def test_a_server_overview_page(dashbord_dir: Path) -> None:
    """Test display a_server_overview.py page."""
    at = AppTest.from_file(f"{dashbord_dir}/pages/a_server_overview.py").run()

    # Check the title
    assert "Lomas configurations" in at.title[0].value

    # Check server URL
    assert "The server is available for requests at the address:" in at.markdown[0].value
    assert "http://localhost:48080" in at.markdown[0].value

    # Server state messages
    assert "The server is live and ready!" in at.markdown[1].value
    assert ":red[The server is in PRODUCTION mode.]" in at.markdown[2].value

    # Check Server configurations
    assert "Server configurations" in at.subheader[0].value
    assert "The host IP of the server is: localhost" in at.markdown[3].value
    assert "The method against timing attack is: jitter" in at.markdown[5].value

    # Check Administration Database information
    assert "Administration Database" in at.subheader[1].value
    assert "Its address is: /tmp/admin.db" in at.markdown[6].value

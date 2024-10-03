import pytest
import streamlit as st
from streamlit.testing import TestApp
from unittest.mock import patch


@pytest.fixture
def app():
    # Create a Streamlit test app instance
    return TestApp(__name__)


def test_about_page(app):
    # Mock the Streamlit functions to avoid side effects
    with patch("streamlit.write") as mock_write, \
         patch("streamlit.header") as mock_header, \
         patch("streamlit.title") as mock_title:
        
        # Import the about.py page to simulate the app running
        from lomas_server.administration.dashboard import about

        # Call the main method or directly reference the execution block in your about.py file
        # It ensures the app runs in the test
        about.main()

        # Assert that key UI elements are rendered
        mock_title.assert_called_once_with("Welcome!")
        mock_header.assert_any_call("Lomas Administation Dashboard")
        mock_header.assert_any_call("Key Features")

        # Assert that text is written to the page
        assert mock_write.call_count > 0  # At least one write should be called

        # Optionally, check for specific calls if you want to ensure specific text is rendered
        mock_write.assert_any_call(
            "The Lomas Administration Dashboard provides a centralized interface for managing various aspects of your server and database."
        )

import unittest
from unittest.mock import patch
import streamlit as st
from st_pages import Page


class TestAboutPage(unittest.TestCase):

    @patch("streamlit.write")
    @patch("streamlit.header")
    @patch("streamlit.title")
    @patch("streamlit.set_page_config")
    @patch("st_pages.show_pages") 
    def test_about_page(self, mock_show_pages, mock_set_page_config, mock_title, mock_header, mock_write):
        from lomas_server.administration.dashboard import about
        about.main()

        mock_set_page_config.assert_called_once_with(page_title="Lomas Dashboard")

        expected_pages = [
            Page("./lomas_server/administration/dashboard/about.py", "Home Page", "🏠"),
            Page("./lomas_server/administration/dashboard/pages/01_server_overview.py", "Lomas server overview", ":computer:"),
            Page("./lomas_server/administration/dashboard/pages/02_database_administration.py", "Admin database management", ":file_folder:")
        ]
        mock_show_pages.assert_called_once_with(expected_pages)

        mock_title.assert_called_once_with("Welcome!")
        mock_header.assert_any_call("Lomas Administation Dashboard")
        mock_header.assert_any_call("Key Features")

        # Get all write calls
        written_texts = [call.args[0] for call in mock_write.call_args_list]
        self.assertTrue(
            any("The Lomas Administration Dashboard provides a centralized interface" in text for text in written_texts)
        )

if __name__ == '__main__':
    unittest.main()

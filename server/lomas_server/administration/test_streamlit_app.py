import unittest
from unittest.mock import patch
import streamlit as st

class TestAboutPage(unittest.TestCase):

    @patch("streamlit.write")
    @patch("streamlit.header")
    @patch("streamlit.title")
    @patch("st_pages.show_pages") 
    def test_about_page(self, mock_show_pages, mock_title, mock_header, mock_write):
        # Mock show_pages since it depends on the Streamlit runtime
        mock_show_pages.return_value = None

        # Import the about.py file and call the main() function
        from lomas_server.administration.dashboard import about
        about.main()

        # Assert that the title is called once with "Welcome!"
        mock_title.assert_called_once_with("Welcome!")

        # Assert that the headers are called with the expected text
        mock_header.assert_any_call("Lomas Administation Dashboard")
        mock_header.assert_any_call("Key Features")

        # Assert that some text has been written to the page
        mock_write.assert_called()  # At least one write should be called

        # Get all write calls
        written_texts = [call.args[0] for call in mock_write.call_args_list]

        # Assert that the expected text is somewhere in the calls
        self.assertTrue(
            any("The Lomas Administration Dashboard provides a centralized interface" in text for text in written_texts)
        )

if __name__ == '__main__':
    unittest.main()

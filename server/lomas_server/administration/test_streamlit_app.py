from streamlit.testing.v1 import AppTest

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

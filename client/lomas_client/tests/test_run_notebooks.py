import pytest

from lomas_client.scripts.run_notebooks import run_notebooks


@pytest.mark.long
def test_run_notebooks():
    """Runs all client notebooks and fails if any of them raises an error."""
    run_notebooks(save_output=False)

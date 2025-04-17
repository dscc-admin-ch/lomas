from pathlib import Path

import pytest

from lomas_client.scripts.run_notebooks import run_notebook


@pytest.mark.long
def test_run_notebook(notebook: Path) -> None:
    """Runs the notebook and fails if the notebook fails.

    Args:
        notebook (str): The notebook file path.
    """
    run_notebook(notebook, save_output=False)

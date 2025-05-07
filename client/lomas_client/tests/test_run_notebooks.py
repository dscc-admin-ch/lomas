from pathlib import Path

import pytest

from lomas_client.scripts.run_notebook import run_notebook


@pytest.mark.long
def test_run_notebook(notebook: Path) -> None:
    """Runs the notebook and fails if the notebook fails.

    Args:
        notebook (str): The notebook file path.
    """
    run_notebook(notebook, True, save_output=False, skip_smartnoise_synth=True)

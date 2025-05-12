from pathlib import Path
from typing import NamedTuple

import pytest

from lomas_client.scripts.run_notebook import get_client_notebook_files, run_notebook


def mark_notebook(notebooks: list[Path]) -> list[NamedTuple]:
    marks = {"Demo_Client_Notebook_Smartnoise-Synth.ipynb": pytest.mark.skip}  # TODO issue 423
    return [pytest.param(file, marks=marks.get(file.name, [])) for file in notebooks]


@pytest.mark.long
@pytest.mark.parametrize("notebook", mark_notebook(get_client_notebook_files()), ids=lambda file: file.name)
def test_run_notebook(notebook: Path) -> None:
    """Runs the notebook and fails if the notebook fails.

    Args:
        notebook (str): The notebook file path.
    """
    run_notebook(notebook, run_demo_setup=True, save_output=False, skip_smartnoise_synth=True)

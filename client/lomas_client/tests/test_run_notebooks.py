from pathlib import Path
from typing import NamedTuple

import pytest

from lomas_client.scripts.run_notebook import get_client_notebook_files, run_notebook


def mark_notebook(notebooks: list[Path]) -> list[NamedTuple]:
    marks = {
        "Demo_Client_Notebook_DiffPrivLib.ipynb": pytest.mark.long,  # ~33s
        "Demo_Client_Notebook.ipynb": pytest.mark.skip(reason="Smartnoise broken with opendp>0.12"),  # ~33s
        "Demo_Client_Notebook_OpenDP_Polars.ipynb": pytest.mark.long,  # ~33s
        "Demo_Client_Notebook_OpenDP_Polars_features.ipynb": pytest.mark.long,
        "Demo_Client_Notebook_Smartnoise-SQL.ipynb": pytest.mark.long,  # ~36s
        "Demo_Client_Notebook_Smartnoise-Synth.ipynb": pytest.mark.skip(reason="Issue #423"),
        "Minimalist_Demo_Client_Notebook.ipynb": pytest.mark.skip(
            reason="Smartnoise broken with opendp>0.12"
        ),  # ~8s
        "Penguin_Research.ipynb": pytest.mark.xfail(reason="How do you even VAR in ODP ???"),  # ~9s
        "Queries Testing.ipynb": pytest.mark.skip(reason="Smartnoise broken with opendp>0.12"),  # ~49s
    }
    return [pytest.param(file, marks=marks.get(file.name, [])) for file in notebooks]


@pytest.mark.parametrize("notebook", mark_notebook(get_client_notebook_files()), ids=lambda file: file.name)
def test_run_notebook(notebook: Path) -> None:
    """Runs the notebook and fails if the notebook fails.

    Args:
        notebook (str): The notebook file path.
    """
    run_notebook(notebook, run_demo_setup=True, save_output=False, skip_smartnoise_synth=True)

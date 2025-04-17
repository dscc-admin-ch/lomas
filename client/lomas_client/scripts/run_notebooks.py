from pathlib import Path

import nbformat
from nbclient import NotebookClient

from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup


def get_client_notebook_files() -> list[Path]:
    """
    Returns a list of the client notebook file names (absolute paths).

    Assumes the file layout is the same as in the code repository.
    """

    return [nb.resolve() for nb in Path(__file__).parent.glob("../../notebooks/*.ipynb")]


def run_notebook(file: Path, save_output: bool = False) -> None:
    """Runs the notebook in the given file.

    Assumes all services in the process compose are up and
    the file layout is same as in the code repository.

    Args:
        file (str): _description_
        save_output (bool, optional): Saves the output to the original file. Defaults to False.
    """
    # Reset demo users and budgets
    lomas_demo_setup()
    nb = nbformat.read(file, as_version=4)
    nb_client = NotebookClient(nb, resources={"metadata": {"path": str(file.parent)}}, timeout=60 * 5)
    nb_client.execute()

    if save_output:
        nbformat.write(nb, file)


def run_notebooks(save_output: bool = False) -> None:
    """Runs all notebooks in the notebooks folder.

    Assumes all services in the process compose are up and
    the file layout is same as in the code repository.

    Args:
        save_output (bool, optional): Saves the output to the original file. Defaults to False.
    """
    notebooks = get_client_notebook_files()

    for file in notebooks:
        print(f"Running {file}.")
        run_notebook(file, save_output)


if __name__ == "__main__":
    run_notebooks(save_output=True)

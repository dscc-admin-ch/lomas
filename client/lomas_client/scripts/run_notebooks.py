import glob

import nbformat
from nbclient import NotebookClient

from lomas_client.tests.utils import get_test_dir
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup


def get_client_notebook_files():
    """
    Returns a list of the client notebook file names (absolute paths).

    Assumes the file layout is the same as in the code repository.
    """
    test_dir = get_test_dir()
    notebooks = glob.glob(f"{test_dir}/../../notebooks/*.ipynb")

    return notebooks


def run_notebooks(save_output: bool = False) -> None:
    """Runs all notebooks in the notebooks folder.

    Assumes all services in the process compose are up and
    the file layout is same as in the code repository.

    Args:
        save_output (bool, optional): Saves the output to the original file. Defaults to False.
    """
    notebooks = get_client_notebook_files()
    for file in notebooks:
        # Reset demo users and budgets
        lomas_demo_setup()
        file = "/home/azureuser/work/sdd-poc-server/client/lomas_client/tests/../../notebooks/Demo_Client_Notebook.ipynb"
        nb = nbformat.read(file, as_version=4)
        nb_client = NotebookClient(nb, resources={"metadata": {"path": f"{get_test_dir()}/../../notebooks/"}})
        nb_client.execute()

        if save_output:
            nbformat.write(nb, file)

        break


if __name__ == "__main__":
    run_notebooks(save_output=True)

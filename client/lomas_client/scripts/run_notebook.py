import argparse
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def get_client_notebook_files() -> list[Path]:
    """
    Returns a list of the client notebook file names (absolute paths).

    Assumes the file layout is the same as in the code repository.
    """

    return [nb.resolve() for nb in Path(__file__).parent.glob("../../notebooks/*.ipynb")]


def run_notebook(
    file: Path, run_demo_setup: bool, save_output: bool = False, skip_smartnoise_synth: bool = True
) -> None:
    """Runs the notebook in the given file.

    Assumes all services in the process compose are up and
    the file layout is same as in the code repository.

    Args:
        file (str): _description_
        run_demo_setup (bool): Runs the lomas_demo_setup before running the notebook.
        save_output (bool, optional): Saves the output to the original file. Defaults to False.
        skip_smartnoise_synth (bool, optional): Skip smartnoise synth demo notebook
    """
    # TODO issue 423
    if skip_smartnoise_synth and file.name == "Demo_Client_Notebook_Smartnoise-Synth.ipynb":
        print("Skiping smartnoise synth notebook.")
        return

    # Reset demo users and budgets
    if run_demo_setup:
        # Import this here so that the script can still be run in environments without the server lib.
        from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup

        lomas_demo_setup()

    nb = nbformat.read(file, as_version=4)
    nb_client = NotebookClient(nb, resources={"metadata": {"path": str(file.parent)}}, timeout=60 * 5)
    nb_client.execute()

    if save_output:
        nbformat.write(nb, file)


if __name__ == "__main__":

    parser = argparse.ArgumentParser("Run client notebooks")
    parser.add_argument("--notebook", type=Path, help="Path to notebook to run.")
    parser.add_argument(
        "--all", "-a", action="store_true", help="Run all notebooks. Ignores the --notebook option."
    )
    parser.add_argument(
        "--run_demo_setup",
        "-d",
        action="store_true",
        help="Run the lomas demo setup before every notebook run.",
    )
    parser.add_argument("--save_output", "-s", action="store_true", help="Save the output to the notebook.")

    args = parser.parse_args()

    # use the notebook given in argument otherwise discover all the client ones
    notebooks = get_client_notebook_files() if args.all else [args.notebook]

    for file in notebooks:
        print(f"Running {file.name}.")
        run_notebook(file, run_demo_setup=args.run_demo_setup, save_output=args.save_output)

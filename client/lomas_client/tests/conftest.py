import os

from lomas_client.scripts.run_notebooks import get_client_notebook_files


def pytest_generate_tests(metafunc):
    """Pytest function to generate test functions for notebook runs.

    Args:
        metafunc (): Pytest metafunc object
    """
    if "notebook" in metafunc.fixturenames:
        notebooks = get_client_notebook_files()

        metafunc.parametrize("notebook", notebooks, ids=os.path.basename)

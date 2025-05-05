import os


def get_test_dir() -> str:
    """Returns the absolute path of the test directory.

    (Based on the fact that this utils file is placed in the test directory).

    Returns:
        str: The absolute path of the test directory.
    """
    this_file_path = os.path.abspath(__file__)
    test_dir = os.path.dirname(this_file_path)

    return test_dir

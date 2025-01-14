import os
from io import BytesIO

import mongomock


def get_mocked_db():
    """Create a mock mondoDB for testing."""
    client = mongomock.MongoClient()
    db = client["test_db"]
    return db


def load_mock_file(file_path: str) -> BytesIO:
    """
    Loads the YAML content from a given file path and returns a.

    mock BytesIO file-like object.
    """
    with open(file_path, "rb") as file:
        mock_file = BytesIO(file.read())
        mock_file.name = os.path.basename(file_path)
    return mock_file

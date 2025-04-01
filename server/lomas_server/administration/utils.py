from urllib.parse import urlparse


def absolute_path(path: str, prefix: str) -> str:
    """Adds the prefix to the path only if the path is a file path and not a url.

    Args:
        path (str): A file path or valid url.
        prefix (str): The prefix to add.

    Returns:
        str: The absolute file path or original url.
    """
    if prefix == "":
        return path

    parsed_path = urlparse(path)

    if parsed_path.scheme in ("http", "https"):
        return path

    return f"{prefix}/{path}"

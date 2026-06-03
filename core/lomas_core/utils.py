from pydantic import AnyUrl


def url_append(url: AnyUrl, path: str) -> AnyUrl:
    """Ensure url/path doesn't have missing/double forward slashes."""
    return url.build(
        scheme=url.scheme,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
        path="/".join((url.path.rstrip("/"), path.lstrip("/"))).lstrip("/"),
        query=url.query,
        fragment=url.fragment,
    )

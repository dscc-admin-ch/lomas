import logging

import uvicorn
from uvicorn.config import LOGGING_CONFIG

from lomas_server.models.config import Config


class FilterOutLiveSuccess:
    """Filter out INFO logs: GET /api/live HTTP/1.1 200 OK."""

    def filter(self, record: logging.LogRecord) -> bool:  # pylint: disable=missing-function-docstring
        (_, _, full_path, _, status_code) = record.args  # type: ignore[misc]
        return not ((full_path == "/api/live") and (int(status_code) == 200))  # type: ignore[arg-type]


def uvicorn_serve() -> None:
    """Start the ASGI server for lomas."""
    config = Config()

    log_config = LOGGING_CONFIG
    log_config["handlers"]["access"]["filters"] = [FilterOutLiveSuccess()]

    uvicorn.run(
        "lomas_server.app:app",
        host=config.server.host_ip,
        port=config.server.host_port,
        log_config=log_config,
        log_level=config.server.log_level,
        workers=1,
        reload=config.server.reload,
        forwarded_allow_ips=config.server.forwarded_allow_ips,
        root_path=config.server.root_path.removeprefix("/"),
        use_colors=True,
    )


if __name__ == "__main__":
    uvicorn_serve()

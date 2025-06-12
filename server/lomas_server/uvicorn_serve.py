import uvicorn

from lomas_server.models.config import Config


def uvicorn_serve() -> None:
    """Start the ASGI server for lomas."""

    config = Config()

    uvicorn.run(
        "lomas_server.app:app",
        host=config.server.host_ip,
        port=config.server.host_port,
        log_level=config.server.log_level,
        workers=1,
        reload=config.server.reload,
    )


if __name__ == "__main__":
    uvicorn_serve()

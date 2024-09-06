import uvicorn

from lomas_server.utils.config import get_config
from lomas_server.utils.logger import LOG

if __name__ == "__main__":
    # os.chdir("/code/")

    config = get_config()

    if config.server.workers != 1:
        LOG.WARN(
            "Only supports one server worker.",
            "Overwriting server.workers config",
            f" from {config.server.workers} to 1.",
        )

    import importlib

    importlib.import_module("lomas_server.app")
    uvicorn.run(
        "lomas_server.app:app",
        host=config.server.host_ip,
        port=config.server.host_port,
        log_level=config.server.log_level,
        workers=1,
        reload=config.server.reload,
    )

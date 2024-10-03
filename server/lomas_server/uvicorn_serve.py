import uvicorn
from lomas_core.logger import LOG

from lomas_server.utils.config import get_config

if __name__ == "__main__":

    config = get_config()

    if config.server.workers != 1:
        LOG.warning(  # pylint: disable=W1201
            "Only supports one server worker."
            + "Overwriting server.workers config"
            + f" from {config.server.workers} to 1.",
        )

    uvicorn.run(
        "lomas_server.app:app",
        host=config.server.host_ip,
        port=config.server.host_port,
        log_level=config.server.log_level,
        workers=1,
        reload=config.server.reload,
    )

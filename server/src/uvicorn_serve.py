import os

import uvicorn
from utils.config import get_config
from utils.loggr import LOG

if __name__ == "__main__":
    os.chdir("/code/")

    config = get_config()

    if config.server.workers != 1:
        LOG.WARNING(
            "Only supports one server worker.",
            "Overwriting server.workers config",
            f" from {config.server.workers} to 1.",
        )

    uvicorn.run(
        "app:app",
        host=config.server.host_ip,
        port=config.server.host_port,
        log_level=config.server.log_level,
        workers=1,
        reload=config.server.reload,
    )

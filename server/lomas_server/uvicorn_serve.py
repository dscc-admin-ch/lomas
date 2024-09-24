import uvicorn
from lomas_core.logger import LOG

from lomas_server.utils.config import get_config

if __name__ == "__main__":

    config = get_config()

    uvicorn.run(
        "lomas_server.app:app",
        host=config.server.host_ip,
        port=config.server.host_port,
        log_level=config.server.log_level,
        reload=config.server.reload,
        timeout_graceful_shutdown=config.server.timeout_graceful_shutdown
    )

from copy import deepcopy

from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from uvicorn.config import LOGGING_CONFIG

from lomas_core.instrumentation import init_telemetry
from lomas_core.models.constants import FilterOutLiveSuccess, get_lomas_logger, init_logging
from lomas_server.dp_queries.dp_libraries.opendp import set_opendp_features_config
from lomas_server.models.config import Config

logger = get_lomas_logger(__name__)


def startup_tasks(config: Config) -> None:
    """Runs all server startup tasks (logging setup, db wipe if needed, bootstrat, etc.).

    Args:
        config (Config): A server config.
    """
    # Init logging
    init_logging(
        name="lomas_server", level=config.server.log_level, lomas_level=config.server.lomas_log_level
    )

    # Initalise telemetry
    if config.telemetry.enabled:
        LoggingInstrumentor().instrument(set_logging_format=True)
        AioPikaInstrumentor().instrument()

        init_telemetry(config.telemetry)

    database = config.database
    if config.clean_admin_database:
        logger.warning(
            "Admin database cleaned at startup. With this option, server restarts will wipe the database!"
        )
        database.wipe()

    # Bootstrap
    if not database.get_bootstrap_disabled():
        logger.info("Setting bootstrap credentials.")
        database.set_bootstrap(config.bootstrap)
    else:
        logger.warning("Not setting bootstrap credentials because already disabled in the admin database")

    # Set DP Libraries config
    set_opendp_features_config(config.opendp_features)


def get_uvicorn_log_config() -> dict:
    """Returns a modified uvicorn logging config that includes timestamps.

    Returns:
        dict: The uvicorn logging config.
    """
    log_config = deepcopy(LOGGING_CONFIG)

    # Remove logs for successfull live calls
    log_config["handlers"]["access"]["filters"] = [FilterOutLiveSuccess()]
    # Add timestamp to log outputs
    for formatter in ["default", "access"]:
        fmt = log_config["formatters"][formatter].get("fmt", "")
        log_config["formatters"][formatter]["fmt"] = f"%(asctime)s {fmt}"
        log_config["formatters"][formatter]["datefmt"] = "[%H:%M:%S]"

    return log_config

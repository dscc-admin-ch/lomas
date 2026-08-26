import asyncio
import contextlib
import functools
import os
import signal
import sys
from collections.abc import AsyncIterator, Iterator
from copy import deepcopy
from pathlib import Path
from typing import Never

from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from uvicorn.config import LOGGING_CONFIG
from watchfiles import awatch

from lomas_core.instrumentation import init_telemetry
from lomas_core.models.constants import FilterOutLiveSuccess, get_lomas_logger, init_logging
from lomas_server.dp_queries.dp_libraries.opendp import set_opendp_features_config
from lomas_server.models.config import Config
from lomas_server.utils.notify import notify

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


class TerminateTaskGroup(Exception):
    """Exception raised to terminate a task group."""


async def force_terminate_task_group() -> Never:
    """Used to force termination of a task group."""
    raise TerminateTaskGroup


def ask_exit(signame: str, tg: asyncio.TaskGroup) -> None:
    """Signal handler for TaskGroup termination."""
    logger.info(f"got signal {signame}: exit")
    tg.create_task(force_terminate_task_group())


class ReloadTaskGroup(Exception):
    """Exception raised to reload a task group."""


async def reload_on_change() -> None:
    includes = ["*.py"]
    excludes = [".*", ".py[cod]", ".sw.*", "~*"]
    watch_root = Path.cwd()
    async for changes in awatch(
        watch_root, watch_filter=None, yield_on_timeout=True, ignore_permission_denied=True
    ):
        unique_paths = {Path(p) for (_, p) in changes}
        change_paths = [
            p for p in unique_paths if any(map(p.match, includes)) and not any(map(p.match, excludes))
        ]
        if len(change_paths) > 0:
            logger.debug(f"Changes detected in {[str(p.relative_to(watch_root)) for p in change_paths]}")
            raise ReloadTaskGroup


@contextlib.contextmanager
def restart_self_on_change() -> Iterator[None]:
    try:
        yield
    except* ReloadTaskGroup:
        os.execl(sys.executable, "python", *sys.argv)


@contextlib.asynccontextmanager
async def interruptible_notify_taskgroup(reload: bool = False) -> AsyncIterator[asyncio.TaskGroup]:
    loop = asyncio.get_running_loop()
    try:
        async with asyncio.TaskGroup() as tg:
            yield tg

            # register signal for polite TaskGroup termination
            for signame in ["SIGINT", "SIGTERM"]:
                loop.add_signal_handler(getattr(signal, signame), functools.partial(ask_exit, signame, tg))

            if reload:
                tg.create_task(reload_on_change())
            notify(b"READY=1")
        # All tasks in Taskgroup are awaited here (aexit of TaskGroup context)
    except* ReloadTaskGroup:
        logger.info("Reloading")
        notify(b"RELOADING=1")
        raise
    except* TerminateTaskGroup:
        logger.info("Terminated")
        notify(b"STOPPING=1")

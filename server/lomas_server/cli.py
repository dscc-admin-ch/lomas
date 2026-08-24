import asyncio
import signal
from typing import Any

import uvicorn
from fastapi import FastAPI
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pydantic_settings import BaseSettings, CliApp, CliSubCommand, SettingsConfigDict
from uvicorn.config import LOGGING_CONFIG

from lomas_core.instrumentation import init_telemetry
from lomas_core.models.constants import FilterOutLiveSuccess, get_lomas_logger, init_logging
from lomas_server.app import get_admin_app, get_user_app
from lomas_server.dp_queries.dp_libraries.opendp import set_opendp_features_config
from lomas_server.models.config import Config
from lomas_server.worker import WorkerConfig

logger = get_lomas_logger(__name__)


class ServiceConfig(Config):
    def cli_cmd(self) -> None:
        """Start the ASGI server for lomas."""
        # Init logging
        init_logging(
            name="lomas_server", level=self.server.log_level, lomas_level=self.server.lomas_log_level
        )
        log_config = LOGGING_CONFIG
        # Remove logs for successfull live calls
        log_config["handlers"]["access"]["filters"] = [FilterOutLiveSuccess()]
        # Add timestamp to log outputs
        for formatter in ["default", "access"]:
            fmt = log_config["formatters"][formatter].get("fmt", "")
            log_config["formatters"][formatter]["fmt"] = f"%(asctime)s {fmt}"
            log_config["formatters"][formatter]["datefmt"] = "[%H:%M:%S]"

        # Initalise telemetry
        if self.telemetry.enabled:
            LoggingInstrumentor().instrument(set_logging_format=True)
            AioPikaInstrumentor().instrument()

            init_telemetry(self.telemetry)

        database = self.database
        if self.clean_admin_database:
            logger.warning(
                "Admin database cleaned at startup. With this option, server restarts will wipe the database!"
            )
            database.wipe()

        # Bootstrap
        if not database.get_bootstrap_disabled():
            logger.info("Setting bootstrap credentials.")
            database.set_bootstrap(self.bootstrap)
        else:
            logger.warning("Not setting bootstrap credentials because already disabled in the admin database")

        # Set DP Libraries config
        set_opendp_features_config(self.opendp_features)

        user_config = uvicorn.Config(
            get_user_app(self),
            host=self.server.host_ip,
            port=self.server.user_host_port,
            log_config=log_config,
            log_level=self.server.log_level,
            workers=1,
            reload=self.server.reload,
            forwarded_allow_ips=self.server.forwarded_allow_ips,
            root_path=self.server.root_path.removeprefix("/"),
            use_colors=True,
        )
        admin_config = uvicorn.Config(
            get_admin_app(self),
            host=self.server.host_ip,
            port=self.server.admin_host_port,
            log_config=log_config,
            log_level=self.server.log_level,
            workers=1,
            reload=self.server.reload,
            forwarded_allow_ips=self.server.forwarded_allow_ips,
            root_path=self.server.root_path.removeprefix("/"),
            use_colors=True,
        )

        user_server = uvicorn.Server(user_config)
        admin_server = uvicorn.Server(admin_config)

        # Catch exit signal to kill both servers (not just one)
        user_server.install_signal_handlers = lambda: None
        admin_server.install_signal_handlers = lambda: None

        def _handle_exit(signum: int, frame: Any) -> None:
            user_server.should_exit = True
            admin_server.should_exit = True

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, _handle_exit)

        async def serve(user_server: FastAPI, admin_server: FastAPI) -> None:
            await asyncio.gather(user_server.serve(), admin_server.serve())

        asyncio.run(serve(user_server, admin_server))


class LomasCli(BaseSettings):
    """Lomas Root Cli."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        use_attribute_docstrings=True,
        cli_parse_args=True,
        cli_kebab_case=True,
        cli_avoid_json=True,
        cli_hide_none_type=True,
        cli_implicit_flags="toggle",
    )

    start: CliSubCommand[ServiceConfig]
    """Starts the Lomas Service."""

    work: CliSubCommand[WorkerConfig]
    """Starts a Lomas Worker."""

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


def run() -> None:
    CliApp.run(LomasCli)


if __name__ == "__main__":
    run()

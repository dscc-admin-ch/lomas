import asyncio

import uvicorn
from pydantic_settings import BaseSettings, CliApp, CliSubCommand, SettingsConfigDict

from lomas_core.models.constants import get_lomas_logger
from lomas_server.app import get_admin_app, get_user_app
from lomas_server.models.config import Config
from lomas_server.utils.startup import (
    get_uvicorn_log_config,
    interruptible_notify_taskgroup,
    restart_self_on_change,
    startup_tasks,
)
from lomas_server.worker import WorkerConfig

logger = get_lomas_logger(__name__)


async def serve(config: Config) -> None:
    """Start lomas server"""
    user_app = get_user_app(config)
    admin_app = get_admin_app(config)

    user_config = uvicorn.Config(
        user_app,
        host=config.server.host_ip,
        port=config.server.user_host_port,
        log_config=get_uvicorn_log_config(),
        log_level=config.server.log_level,
        workers=1,
        reload=config.server.reload,
        forwarded_allow_ips=config.server.forwarded_allow_ips,
        root_path=config.server.root_path.removeprefix("/"),
        use_colors=True,
    )
    admin_config = uvicorn.Config(
        admin_app,
        host=config.server.host_ip,
        port=config.server.admin_host_port,
        log_config=get_uvicorn_log_config(),
        log_level=config.server.log_level,
        workers=1,
        reload=config.server.reload,
        forwarded_allow_ips=config.server.forwarded_allow_ips,
        root_path=config.server.root_path.removeprefix("/"),
        use_colors=True,
    )

    user_server = uvicorn.Server(user_config)
    admin_server = uvicorn.Server(admin_config)

    # Catch exit signal to kill both servers (not just one)
    # user_server.install_signal_handlers = lambda: None
    # admin_server.install_signal_handlers = lambda: None

    # def _handle_exit(signum: int, frame: Any) -> None:
    #     user_server.should_exit = True
    #     admin_server.should_exit = True

    # for sig in (signal.SIGINT, signal.SIGTERM):
    #     signal.signal(sig, _handle_exit)

    # Startup tasks
    startup_tasks(config)

    # Start servers
    async with interruptible_notify_taskgroup(reload=True) as tg:
        tg.create_task(user_server.serve())
        tg.create_task(admin_server.serve())
        await asyncio.gather(user_app.state.ready_event.wait(), admin_app.state.ready_event.wait())


class ServiceConfig(Config):
    def cli_cmd(self) -> None:
        """Start the ASGI server for lomas."""
        with restart_self_on_change():
            asyncio.run(serve(self))


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

    def cli_cmd(config) -> None:
        CliApp.run_subcommand(config)


def run() -> None:
    CliApp.run(LomasCli)


if __name__ == "__main__":
    run()

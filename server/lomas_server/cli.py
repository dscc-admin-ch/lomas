import uvicorn
from pydantic_settings import BaseSettings, CliApp, CliSubCommand, SettingsConfigDict
from uvicorn.config import LOGGING_CONFIG

from lomas_core.models.constants import FilterOutLiveSuccess
from lomas_server.models.config import Config
from lomas_server.worker import WorkerConfig


class ServiceConfig(Config):
    def cli_cmd(self) -> None:
        """Start the ASGI server for lomas."""
        log_config = LOGGING_CONFIG
        # Remove logs for successfull live calls
        log_config["handlers"]["access"]["filters"] = [FilterOutLiveSuccess()]
        # Add timestamp to log outputs
        for formatter in ["default", "access"]:
            fmt = log_config["formatters"][formatter].get("fmt", "")
            log_config["formatters"][formatter]["fmt"] = f"%(asctime)s {fmt}"
            log_config["formatters"][formatter]["datefmt"] = "[%H:%M:%S]"

        uvicorn.run(
            "lomas_server.app:app",
            host=self.server.host_ip,
            port=self.server.host_port,
            log_config=log_config,
            log_level=self.server.log_level,
            workers=1,
            reload=self.server.reload,
            forwarded_allow_ips=self.server.forwarded_allow_ips,
            root_path=self.server.root_path.removeprefix("/"),
            use_colors=True,
        )


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

import asyncio
import contextlib
import functools
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Never

import httpx2
from aio_pika.patterns.rpc import Proxy
from csvw_eo.metadata_structure import TableMetadata
from fastapi import status
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from returns.io import IOFailure, IOSuccess
from returns.result import Success
from returns.unsafe import unsafe_perform_io
from rich.progress import BarColumn, Progress, SpinnerColumn, TimeElapsedColumn
from watchfiles import awatch

from lomas_core.exceptions import InternalServerException
from lomas_core.instrumentation import init_telemetry
from lomas_core.models.collections import (
    DSInfo,
    User,
)
from lomas_core.models.constants import JobStatus, LomasHeaders, get_lomas_logger, init_logging
from lomas_core.models.requests import (
    CostQueryModel,
    DiffPrivLibRequestModel,
    DummyQueryModel,
    OpenDPRequestModel,
    QueryModel,
    SmartnoiseSQLRequestModel,
)
from lomas_core.models.responses import (
    Budget,
    CostResponse,
    Job,
    QueryResponse,
)
from lomas_server.dp_queries.dp_libraries.diffprivlib import DiffPrivLibQuerier
from lomas_server.dp_queries.dp_libraries.opendp import OpenDPQuerier, set_opendp_features_config
from lomas_server.dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier
from lomas_server.dp_queries.dp_querier import DPQuerier
from lomas_server.dp_queries.dummy_dataset import get_dummy_dataset_for_query
from lomas_server.models.config import Config
from lomas_server.routes.error_handler import model_from_lomas_exception
from lomas_server.routes.utils import get_dataset_connector
from lomas_server.utils.notify import notify
from lomas_server.utils.query import query_lomas

logger = get_lomas_logger(__name__)

# TODO: deployment key & fun
TEST_APIKEY = "worker-api-key"

job_progress = Progress(
    "[turquoise2]{task.description}",
    "[pink1]{task.fields[job].query.library}",
    "[khaki1]{task.fields[job].query.request_type}",
    "[plum2]{task.fields[requested_by]}",
    "[light_green]{task.fields[dataset_name]}",
    SpinnerColumn(),
    BarColumn(),
    TimeElapsedColumn(),
)


def admin_database_proxy(method_name: str, kwargs: dict[str, Any]) -> Any:
    match (method_name, kwargs):
        case ("get_remaining_budget", {"user_name": user_name, "dataset_name": dataset_name}):
            res = query_lomas(
                "/w/get_remaining_budget",
                httpx2.post,
                headers={LomasHeaders.APIKEY: TEST_APIKEY, LomasHeaders.FORUSER: user_name},
                json={"dataset_name": dataset_name},
            ).map(Budget.model_validate)
            return unsafe_perform_io(res.value_or(None))

        case ("get_dataset_metadata", {"dataset_name": dataset_name}):
            res = query_lomas(
                f"/w/dataset/{dataset_name}/metadata",
                httpx2.get,
                headers={LomasHeaders.APIKEY: TEST_APIKEY},
            ).map(TableMetadata.model_validate)
            return unsafe_perform_io(res.value_or(None))

        case ("get_dataset", {"dataset_name": dataset_name}):
            res = query_lomas(
                f"/w/dataset/{dataset_name}", httpx2.get, headers={LomasHeaders.APIKEY: TEST_APIKEY}
            ).map(DSInfo.model_validate)
            return unsafe_perform_io(res.value_or(None))

        case ("get_user", {"user_name": user_name}):
            # TODO: should this mechanic be changed ? do we even want to attempt Semaphore over network ?
            res = query_lomas(
                f"/w/users/{user_name}", httpx2.get, headers={LomasHeaders.APIKEY: TEST_APIKEY}
            ).map(User.model_validate)
            return unsafe_perform_io(res.value_or(None))

        case _:
            raise ValueError(f"Invalid Proxy method: {method_name}")


def handle_query(config: Config, admin_database: Proxy, job: Job) -> Job:
    """Handle queries."""
    start_sec = time.time()
    logger.debug("Handling query.")

    try:
        query_model = job.query
        assert query_model is not None
        user_name = job.requested_by
        assert user_name is not None

        if isinstance(query_model, DummyQueryModel):
            data_connector = get_dummy_dataset_for_query(admin_database, query_model)
        else:
            data_connector = get_dataset_connector(
                admin_database, query_model.dataset_name, config.private_db_credentials
            )

        dp_querier: DPQuerier
        match query_model:
            case SmartnoiseSQLRequestModel():
                dp_querier = SmartnoiseSQLQuerier(data_connector, admin_database)
            case OpenDPRequestModel():
                dp_querier = OpenDPQuerier(data_connector, admin_database)
            case DiffPrivLibRequestModel():
                dp_querier = DiffPrivLibQuerier(data_connector, admin_database)
            case _:
                raise InternalServerException(f"Library not supported: {query_model.library}")

        match query_model:
            case CostQueryModel():
                budget_cost = dp_querier.cost(query_model)
                query_response = CostResponse(epsilon=budget_cost.epsilon, delta=budget_cost.delta)
            case DummyQueryModel():
                budget_cost = dp_querier.cost(query_model)
                result = dp_querier.query(query_model)
                query_response = QueryResponse(
                    requested_by=user_name,
                    result=result,
                    epsilon=budget_cost.epsilon,
                    delta=budget_cost.delta,
                )
            case QueryModel():
                query_response = dp_querier.handle_query(query_model, user_name)

        job.result = query_response
        job.status = JobStatus.COMPLETE
        job.status_code = status.HTTP_200_OK

        elapsed = time.time() - start_sec
        logger.debug(f"Done ({elapsed:.2f})")

        return job

    except Exception as exc:  # pylint: disable=broad-exception-caught
        error_model, status_code = model_from_lomas_exception(exc)

        job.status = JobStatus.FAILED
        job.error = error_model
        job.status_code = status_code

        return job


async def process_message(config: Config) -> None:
    """General Job processing loop."""
    with contextlib.ExitStack() as stack:
        consecutive_sleep = 0
        status = None
        if config.tui:
            status = stack.enter_context(job_progress.console.status("Polling ..."))
            stack.enter_context(job_progress)

        while True:
            if status is not None:
                status.update(status=f"Polling ... {consecutive_sleep}")
            consecutive_sleep += 1
            await asyncio.sleep(2)

            res = query_lomas("/w/job/pending", httpx2.get, headers={LomasHeaders.APIKEY: TEST_APIKEY})
            match res:
                case IOSuccess(Success(None)):
                    if not config.tui:
                        logger.debug("No pending Jobs - Waiting")
                case IOSuccess(Success(job_json)):
                    job = Job.model_validate(job_json)

                    task_id = job_progress.add_task(
                        f"{job.uid}",
                        total=1,
                        requested_by=job.requested_by,
                        dataset_name=job.dataset_name,
                        job=job,
                    )

                    job_done = handle_query(config, Proxy(admin_database_proxy), job)
                    job_progress.update(task_id, completed=1)
                    if job_done.status == JobStatus.FAILED:
                        job_progress.update(task_id, description="[red]FAILED")

                    res = query_lomas(
                        "/w/job",
                        httpx2.put,
                        headers={LomasHeaders.APIKEY: TEST_APIKEY},
                        json=job_done.model_dump(
                            exclude_unset=True, mode="json"
                        ),  # Requires json mode to make UUID (not json serializable) into str.
                    )
                    consecutive_sleep = 0
                case IOFailure(e):
                    logger.warn(str(e))


class TerminateTaskGroup(Exception):
    """Exception raised to terminate a task group."""


class ReloadTaskGroup(Exception):
    """Exception raised to reload a task group."""


async def force_terminate_task_group() -> Never:
    """Used to force termination of a task group."""
    raise TerminateTaskGroup


def ask_exit(signame: str, tg: asyncio.TaskGroup) -> None:
    """Signal handler for TaskGroup termination."""
    logger.info(f"got signal {signame}: exit")
    tg.create_task(force_terminate_task_group())


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


async def process_queue(config: Config) -> None:
    """Handle & await all pika processing queues."""
    loop = asyncio.get_running_loop()
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(process_message(config))

            # register signal for polite TaskGroup termination
            for signame in ["SIGINT", "SIGTERM"]:
                loop.add_signal_handler(getattr(signal, signame), functools.partial(ask_exit, signame, tg))

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


class WorkerConfig(Config):
    def cli_cmd(self) -> None:
        run(self)


def run(config: Config | None = None) -> None:
    """Start the Worker loop."""
    if config is None:
        config = Config()

    init_logging(
        name="lomas_server",
        level=config.server.log_level,
        lomas_level=config.server.lomas_log_level,
        console=job_progress.console if config.tui else None,
    )

    set_opendp_features_config(config.opendp_features)

    if config.telemetry.enabled:
        LoggingInstrumentor().instrument(set_logging_format=True)
        AioPikaInstrumentor().instrument()
        init_telemetry(config.telemetry)

    logger.info("Waiting for messages. To exit press CTRL+C")
    try:
        asyncio.run(process_queue(config))
    except* ReloadTaskGroup:
        os.execl(sys.executable, "python", *sys.argv)


if __name__ == "__main__":
    run()

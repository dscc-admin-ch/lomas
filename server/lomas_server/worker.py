import contextlib
import time
import types
from collections.abc import Callable
from functools import partial
from typing import Any

import anyio
import httpx2
from aio_pika.patterns.rpc import Proxy
from csvw_eo.metadata_structure import TableMetadata
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from returns.functions import raise_exception
from returns.result import Failure, ResultE, Success
from rich.progress import BarColumn, Progress, SpinnerColumn, TimeElapsedColumn

from lomas_core.instrumentation import init_telemetry
from lomas_core.models.collections import DSInfo
from lomas_core.models.constants import LomasHeaders, get_lomas_logger, init_logging
from lomas_core.models.requests import (
    AnyLomasRequest,
    CostQueryModel,
    DiffPrivLibRequestModel,
    DummyQueryModel,
    OpenDPRequestModel,
    QueryModel,
    SmartnoiseSQLRequestModel,
)
from lomas_core.models.responses import (
    AnyLomasQueryResponse,
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
from lomas_server.models.config import WorkerConfig
from lomas_server.routes.utils import get_dataset_connector
from lomas_server.utils.query import query_lomas
from lomas_server.utils.startup import (
    interruptible_notify_taskgroup,
    restart_self_on_change,
)

logger = get_lomas_logger(__name__)

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


def admin_database_proxy(
    config: WorkerConfig, client: types.ModuleType, method_name: str, kwargs: dict[str, Any]
) -> Any:
    """Meant to be used as partial function to implement AdminDatabase methods necessary for handling queries (cost, dummy and real queries)."""
    match (method_name, kwargs):
        case ("get_remaining_budget", {"user_name": user_name, "dataset_name": dataset_name}):
            res = query_lomas(
                "/w/get_remaining_budget",
                client.post,
                host=config.admin_api,
                headers={LomasHeaders.APIKEY: config.worker_api_key, LomasHeaders.FORUSER: user_name},
                json={"dataset_name": dataset_name},
            ).map(Budget.model_validate)

        case ("get_dataset_metadata", {"dataset_name": dataset_name}):
            res = query_lomas(
                f"/w/dataset/{dataset_name}/metadata",
                client.get,
                host=config.admin_api,
                headers={LomasHeaders.APIKEY: config.worker_api_key},
            ).map(TableMetadata.model_validate)

        case ("get_dataset", {"dataset_name": dataset_name}):
            res = query_lomas(
                f"/w/dataset/{dataset_name}",
                client.get,
                host=config.admin_api,
                headers={LomasHeaders.APIKEY: config.worker_api_key},
            ).map(DSInfo.model_validate)

        case _:
            raise ValueError(f"Invalid Proxy method: {method_name}")
    # Exceptions will end up wrapped in InternalServerExceptions and result in failed jobs.
    # Rationale: scenarios from which we can recover are too few and rather unlikely.
    return res.alt(raise_exception).unwrap()


def handle_query(config: WorkerConfig, admin_database: Proxy, job: Job) -> Job:
    """Handle queries."""
    start_sec = time.time()
    logger.debug("Handling query.")

    try:
        assert job.query is not None  # type narrowing
        query_model: AnyLomasRequest = job.query
        user_name: str = job.requested_by

        if isinstance(query_model, DummyQueryModel):
            data_connector = get_dummy_dataset_for_query(admin_database, query_model)
        else:
            data_connector = get_dataset_connector(
                admin_database, query_model.dataset_name, config.private_db_credentials
            )

        dp_querier: DPQuerier
        query_response: AnyLomasQueryResponse
        match query_model:
            case SmartnoiseSQLRequestModel():
                dp_querier = SmartnoiseSQLQuerier(data_connector, admin_database)
            case OpenDPRequestModel():
                dp_querier = OpenDPQuerier(data_connector, admin_database)
            case DiffPrivLibRequestModel():
                dp_querier = DiffPrivLibQuerier(data_connector, admin_database)

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

        elapsed = time.time() - start_sec
        logger.debug(f"Done ({elapsed:.2f})")

        return job.complete(query_response)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        return job.fail(exc)


def get_next_job(config: WorkerConfig, client: types.ModuleType) -> ResultE[Job | None]:
    """Get next pending job from server. Returns the job as a ResultE."""
    return query_lomas(
        "/w/job/pending",
        client.get,
        host=config.admin_api,
        headers={LomasHeaders.APIKEY: config.worker_api_key},
    ).map(lambda job_json: Job.model_validate(job_json) if job_json is not None else None)


def job_post_process(config: WorkerConfig, client: types.ModuleType, job_done: Job) -> ResultE[Job | None]:
    """Return job to server. Returns the job as a ResultE."""
    return query_lomas(
        "/w/job",
        client.put,
        host=config.admin_api,
        headers={LomasHeaders.APIKEY: config.worker_api_key},
        json=job_done.model_dump(
            exclude_unset=True, mode="json"
        ),  # Requires json mode to make UUID (not json serializable) into str.
    ).map(lambda _: job_done)


async def worker_loop(config: WorkerConfig, client: types.ModuleType = httpx2) -> None:
    """General worker processing loop."""
    with contextlib.ExitStack() as stack:
        status, err_msg = None, ""
        if config.tui:
            status = stack.enter_context(job_progress.console.status("Polling ..."))
            stack.enter_context(job_progress)

        consecutive_sleep = 0
        while True:
            if status is not None:
                status.update(status=f"Polling ... {consecutive_sleep}{err_msg}")
                err_msg = ""

            await anyio.sleep(
                min(config.worker_loop_init_delay * 1.5**consecutive_sleep, config.worker_loop_max_delay)
            )

            step_result = worker_step(config, client)

            consecutive_sleep += 1
            match step_result:
                case Success(Job()):
                    consecutive_sleep = 0
                case Success(None):
                    if not config.tui:
                        logger.debug("No pending Jobs - Waiting")
                case Failure(httpx2.HTTPError() as e):
                    if status is not None:
                        err_msg = f"     [bold red]{e}[/bold red]"
                    else:
                        logger.warning(str(e))
                case Failure(e):
                    logger.warning(str(e))


def worker_step(
    config: WorkerConfig,
    client: types.ModuleType = httpx2,
    get_next_job: Callable[[WorkerConfig, types.ModuleType], ResultE[Job | None]] = get_next_job,
    job_post_process: Callable[[WorkerConfig, types.ModuleType, Job], ResultE[Job | None]] = job_post_process,
) -> ResultE[Job | None]:
    """Runs a single worker step.

    Gets a job, executes it and returns the result to the server.

    Args:
        config (WorkerConfig): The worker config.
        client (types.ModuleType, optional): The client to use to reach the server. Defaults to httpx2.
        get_next_job (Callable[[WorkerConfig, types.ModuleType], ResultE[Job  |  None]], optional): Callable to get next job. Defaults to get_next_job.
        job_post_process (Callable[[WorkerConfig, types.ModuleType, Job], ResultE[Job  |  None]], optional): Callable for post job step. Defaults to job_post_process.

    Returns:
        ResultE[Job | None]: The result containing the finished job or any failure along the way.
    """
    match get_next_job(config, client):
        case Success(Job() as job):
            task_id = job_progress.add_task(
                f"{job.uid}",
                total=1,
                requested_by=job.requested_by,
                dataset_name=job.dataset_name,
                job=job,
            )

            job_done = handle_query(config, Proxy(partial(admin_database_proxy, config, client)), job)
            job_progress.update(task_id, completed=1)
            if job_done.failure():
                job_progress.update(task_id, description="[red]FAILED[/red]")

            return job_post_process(config, client, job_done)
        case _ as res:
            return res


async def start_worker_loop(config: WorkerConfig) -> None:
    """Start interruptible task with worker loop."""
    async with interruptible_notify_taskgroup(reload=config.reload) as tg:
        tg.create_task(worker_loop(config))


class WorkerCliConfig(WorkerConfig):
    def cli_cmd(self) -> None:
        run(self)


def run(config: WorkerConfig | None = None) -> None:
    """Start the Worker loop."""
    if config is None:
        config = WorkerConfig()

    init_logging(
        name="lomas_server",
        level=config.log_level,
        lomas_level=config.lomas_log_level,
        console=job_progress.console if config.tui else None,
    )

    set_opendp_features_config(config.opendp_features)

    if config.telemetry.enabled:
        LoggingInstrumentor().instrument(set_logging_format=True)
        AioPikaInstrumentor().instrument()
        init_telemetry(config.telemetry)

    logger.info("Waiting for messages. To exit press CTRL+C")
    with restart_self_on_change():
        anyio.run(start_worker_loop, config)


if __name__ == "__main__":
    run()

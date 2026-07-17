import asyncio
import functools
import signal
import time
from collections.abc import Callable
from functools import partial
from typing import Any, Never
from uuid import UUID

import aio_pika
from aio_pika.patterns.rpc import RPC, Proxy
from fastapi import status
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from lomas_core.exceptions import InternalServerException
from lomas_core.instrumentation import init_telemetry
from lomas_core.models.constants import JobStatus, get_lomas_logger, init_logging
from lomas_core.models.requests import (
    CostQueryModel,
    DiffPrivLibRequestModel,
    DummyQueryModel,
    OpenDPRequestModel,
    QueryModel,
    SmartnoiseSQLRequestModel,
)
from lomas_core.models.responses import CostResponse, Job, QueryResponse
from lomas_server.dp_queries.dp_libraries.diffprivlib import DiffPrivLibQuerier
from lomas_server.dp_queries.dp_libraries.opendp import OpenDPQuerier, set_opendp_features_config
from lomas_server.dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier
from lomas_server.dp_queries.dp_querier import DPQuerier
from lomas_server.dp_queries.dummy_dataset import get_dummy_dataset_for_query
from lomas_server.models.config import Config
from lomas_server.routes.error_handler import model_from_lomas_exception
from lomas_server.routes.utils import get_dataset_connector, rabbitmq_connect_queue
from lomas_server.utils.notify import notify

logger = get_lomas_logger(__name__)


async def handle_query(config: Config, admin_database: Proxy, message: aio_pika.IncomingMessage) -> Job:
    """Handle queries."""
    start_sec = time.time()
    logger.debug("Handling query.")

    try:
        body = message.body.decode()
        job = Job.model_validate_json(body)

        query_model = job.query
        assert query_model is not None
        user_name = job.requested_by
        assert user_name is not None

        if isinstance(query_model, DummyQueryModel):
            data_connector = await get_dummy_dataset_for_query(admin_database, query_model)
        else:
            data_connector = await get_dataset_connector(
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
                eps_cost, delta_cost = dp_querier.cost(query_model)
                query_response = CostResponse(epsilon=eps_cost, delta=delta_cost)
            case DummyQueryModel():
                eps_cost, delta_cost = dp_querier.cost(query_model)
                result = dp_querier.query(query_model)
                query_response = QueryResponse(
                    requested_by=user_name, result=result, epsilon=eps_cost, delta=delta_cost
                )
            case QueryModel():
                query_response = await dp_querier.handle_query(query_model, user_name)

        job.result = query_response
        job.status = JobStatus.COMPLETE
        job.status_code = status.HTTP_200_OK

        elapsed = time.time() - start_sec
        logger.debug(f"Done ({elapsed:.2f})")

        return job

    except Exception as exc:  # pylint: disable=broad-exception-caught
        error_model, status_code = model_from_lomas_exception(exc)

        return Job(
            uid=UUID(message.correlation_id),
            status=JobStatus.FAILED,
            error=error_model,
            status_code=status_code,
        )


async def process_message(
    channel: aio_pika.Channel,
    in_queue: str,
    out_queue: str,
    message_handler: Callable[[aio_pika.IncomingMessage], Any],
) -> None:
    """General RabbitMQ Message handler -> processing -> response."""
    queue = await channel.declare_queue(in_queue, durable=True)
    await channel.declare_queue(out_queue, durable=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                headers = None
                body = b""
                job = await message_handler(message)
                body = job.model_dump_json(exclude_unset=True).encode()

                await channel.default_exchange.publish(
                    aio_pika.Message(headers=headers, body=body, correlation_id=message.correlation_id),
                    routing_key=out_queue,
                )


class TerminateTaskGroup(Exception):
    """Exception raised to terminate a task group."""


async def force_terminate_task_group() -> Never:
    """Used to force termination of a task group."""
    raise TerminateTaskGroup


def ask_exit(signame: str, tg: asyncio.TaskGroup) -> None:
    """Signal handler for TaskGroup termination."""
    logger.info(f"got signal {signame}: exit")
    tg.create_task(force_terminate_task_group())


async def process_queue(config: Config) -> None:
    """Handle & await all pika processing queues."""
    loop = asyncio.get_running_loop()
    connection = await rabbitmq_connect_queue(config)

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        rpc = await RPC.create(channel, durable=True)

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(
                    process_message(
                        channel, "task_queue", "task_response", partial(handle_query, config, rpc.proxy)
                    )
                )

                # register signal for polite TaskGroup termination
                for signame in ["SIGINT", "SIGTERM"]:
                    loop.add_signal_handler(
                        getattr(signal, signame), functools.partial(ask_exit, signame, tg)
                    )
                notify(b"READY=1")
            # All tasks in Taskgroup are awaited here (aexit of TaskGroup context)
        except* TerminateTaskGroup:
            logger.info("Terminated")
            notify(b"STOPPING=1")
        finally:
            await channel.close()
            await connection.close()


def run() -> None:
    """Start the Worker loop."""
    config = Config()
    init_logging(
        name="lomas_server", level=config.server.log_level, lomas_level=config.server.lomas_log_level
    )

    set_opendp_features_config(config.opendp_features)

    if config.telemetry.enabled:
        LoggingInstrumentor().instrument(set_logging_format=True)
        AioPikaInstrumentor().instrument()
        init_telemetry(config.telemetry)

    logger.info("Waiting for messages. To exit press CTRL+C")
    asyncio.run(process_queue(config))


if __name__ == "__main__":
    run()

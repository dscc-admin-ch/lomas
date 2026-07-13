import asyncio
import functools
import signal
import time
from collections.abc import Callable
from functools import partial
from typing import Any, Never

import aio_pika
from aio_pika.patterns.rpc import RPC, Proxy
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from lomas_core.constants import DPLibraries
from lomas_core.exceptions import InternalServerException, LomasAPIException
from lomas_core.instrumentation import init_telemetry
from lomas_core.models.constants import get_lomas_logger, init_logging
from lomas_core.models.requests import (
    DiffPrivLibDummyQueryModel,
    DiffPrivLibQueryModel,
    DiffPrivLibRequestModel,
    OpenDPDummyQueryModel,
    OpenDPQueryModel,
    OpenDPRequestModel,
    SmartnoiseSQLDummyQueryModel,
    SmartnoiseSQLQueryModel,
    SmartnoiseSQLRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse
from lomas_server.data_connector import ConnectorUnionTA
from lomas_server.dp_queries.dp_libraries.diffprivlib import DiffPrivLibQuerier
from lomas_server.dp_queries.dp_libraries.opendp import OpenDPQuerier, set_opendp_features_config
from lomas_server.dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier
from lomas_server.dp_queries.dp_querier import DPQuerier
from lomas_server.dp_queries.dummy_dataset import get_dummy_dataset_for_query
from lomas_server.models.config import Config
from lomas_server.routes.error_handler import response_from_lomas_exception
from lomas_server.routes.utils import notify, rabbitmq_connect_queue

logger = get_lomas_logger(__name__)


def handle_exceptions(exc: BaseException) -> JSONResponse:
    """Transform LomasAPIException into a JSONResponse.

    TODO use already defined handlers instead?

    In case of unkown exception, wraps it up as if it were an InternalServerException.
    In case of internal exception, the error message is not forwarded to avoid potentially
    disclosing sensitive information.
    """
    logger.exception(exc)
    match exc:
        case LomasAPIException():
            # same as exception handler
            return response_from_lomas_exception(exc)
        case _:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=jsonable_encoder(InternalServerException()),
            )


async def handle_cost_query(admin_database: Proxy, body: bytes) -> CostResponse | tuple[bytes, int]:
    """Handle Cost query into CostResponse."""
    start_sec = time.time()
    logger.debug("Handling cost query.")
    message = body.decode()
    _, dp_library, data_connector_str, request_model_str = message.split("λ", 3)

    data_connector = ConnectorUnionTA.validate_json(data_connector_str)

    dp_querier: DPQuerier
    match dp_library:
        case DPLibraries.SMARTNOISE_SQL:
            request_model = SmartnoiseSQLRequestModel.model_validate_json(request_model_str)
            dp_querier = SmartnoiseSQLQuerier(data_connector, admin_database)

        case DPLibraries.OPENDP:
            request_model = OpenDPRequestModel.model_validate_json(request_model_str)
            dp_querier = OpenDPQuerier(data_connector, admin_database)

        case DPLibraries.DIFFPRIVLIB:
            request_model = DiffPrivLibRequestModel.model_validate_json(request_model_str)
            dp_querier = DiffPrivLibQuerier(data_connector, admin_database)

    try:
        eps_cost, delta_cost = dp_querier.cost(request_model)
        elapsed = time.time() - start_sec
        logger.debug(f"Done ({elapsed:.2f})")
        return CostResponse(epsilon=eps_cost, delta=delta_cost)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        known_exc = handle_exceptions(exc)
        return known_exc.body, known_exc.status_code


async def handle_query(admin_database: Proxy, body: bytes) -> QueryResponse | tuple[bytes, int]:
    """Handle DP query into QueryResponse."""
    start_sec = time.time()
    logger.debug("Handling query.")
    message = body.decode()
    user_name, dp_library, data_connector_str, query_json_str = message.split("λ", 3)

    data_connector = ConnectorUnionTA.validate_json(data_connector_str)

    dp_querier: DPQuerier
    match dp_library:
        case DPLibraries.SMARTNOISE_SQL:
            query_json = SmartnoiseSQLQueryModel.model_validate_json(query_json_str)
            dp_querier = SmartnoiseSQLQuerier(data_connector, admin_database)

        case DPLibraries.OPENDP:
            query_json = OpenDPQueryModel.model_validate_json(query_json_str)
            dp_querier = OpenDPQuerier(data_connector, admin_database)

        case DPLibraries.DIFFPRIVLIB:
            query_json = DiffPrivLibQueryModel.model_validate_json(query_json_str)
            dp_querier = DiffPrivLibQuerier(data_connector, admin_database)

    try:
        query_response = await dp_querier.handle_query(query_json, user_name)
        elapsed = time.time() - start_sec
        logger.debug(f"Done ({elapsed:.2f})")
        return query_response
    except Exception as exc:  # pylint: disable=broad-exception-caught
        known_exc = handle_exceptions(exc)
        return known_exc.body, known_exc.status_code


async def handle_dummy_query(admin_database: Proxy, body: bytes) -> QueryResponse | tuple[bytes, int]:
    """Handle DP-dummy query into QueryResponse."""
    start_sec = time.time()
    logger.debug("Handling dummy query.")
    message = body.decode()
    user_name, dp_library, data_connector, query_model_str = message.split("λ", 3)

    dp_querier: DPQuerier
    match dp_library:
        case DPLibraries.SMARTNOISE_SQL:
            query_model = SmartnoiseSQLDummyQueryModel.model_validate_json(query_model_str)
            data_connector = await get_dummy_dataset_for_query(admin_database, query_model)
            dp_querier = SmartnoiseSQLQuerier(data_connector, admin_database)

        case DPLibraries.OPENDP:
            query_model = OpenDPDummyQueryModel.model_validate_json(query_model_str)
            data_connector = await get_dummy_dataset_for_query(admin_database, query_model)
            dp_querier = OpenDPQuerier(data_connector, admin_database)

        case DPLibraries.DIFFPRIVLIB:
            query_model = DiffPrivLibDummyQueryModel.model_validate_json(query_model_str)
            data_connector = await get_dummy_dataset_for_query(admin_database, query_model)
            dp_querier = DiffPrivLibQuerier(data_connector, admin_database)

    try:
        eps_cost, delta_cost = dp_querier.cost(query_model)
        result = dp_querier.query(query_model)
        dummy_query_response = QueryResponse(
            requested_by=user_name, result=result, epsilon=eps_cost, delta=delta_cost
        )
        elapsed = time.time() - start_sec
        logger.debug(f"Done ({elapsed:.2f})")
        return dummy_query_response
    except Exception as exc:  # pylint: disable=broad-exception-caught
        known_exc = handle_exceptions(exc)
        return known_exc.body, known_exc.status_code


async def process_message(
    channel: aio_pika.Channel, in_queue: str, out_queue: str, message_handler: Callable[[bytes], Any]
) -> None:
    """General RabbitMQ Message handler -> processing -> response."""
    queue = await channel.declare_queue(in_queue, durable=True)
    await channel.declare_queue(out_queue, durable=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                headers = None
                body = b""
                match await message_handler(message.body):
                    case (bytes(exc_body), int(status_code)):
                        headers = {"type": "exception", "status_code": status_code}
                        logger.debug(headers)
                        body = exc_body

                    case query_response:
                        logger.debug(
                            f"Response length: {len(query_response.model_dump_json())} {message.correlation_id}"
                        )
                        # logger.debug(query_response.model_dump_json())
                        body = query_response.model_dump_json().encode()

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


async def process_all_queues(config: Config) -> None:
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
                    process_message(channel, "task_queue", "task_response", partial(handle_query, rpc.proxy))
                )
                tg.create_task(
                    process_message(
                        channel, "cost_queue", "cost_response", partial(handle_cost_query, rpc.proxy)
                    )
                )
                tg.create_task(
                    process_message(
                        channel, "dummy_queue", "dummy_response", partial(handle_dummy_query, rpc.proxy)
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
    asyncio.run(process_all_queues(config))


if __name__ == "__main__":
    run()

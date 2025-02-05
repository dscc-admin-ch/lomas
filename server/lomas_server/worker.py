import asyncio
import functools
import logging
import os
import signal
import time

import aio_pika
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    KNOWN_EXCEPTIONS,
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
    UnauthorizedAccessException,
)
from lomas_core.instrumentation import get_ressource, init_telemetry
from lomas_core.models.exceptions import (
    ExternalLibraryExceptionModel,
    InternalServerExceptionModel,
    InvalidQueryExceptionModel,
    UnauthorizedAccessExceptionModel,
)
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
    SmartnoiseSynthDummyQueryModel,
    SmartnoiseSynthQueryModel,
    SmartnoiseSynthRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse
from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.constants import SERVER_SERVICE_NAME, SERVICE_ID, TELEMETRY
from lomas_server.data_connector.factory import data_connector_factory
from lomas_server.dp_queries.dp_libraries.factory import querier_factory
from lomas_server.dp_queries.dp_libraries.opendp import set_opendp_features_config
from lomas_server.dp_queries.dummy_dataset import get_dummy_dataset_for_query
from lomas_server.utils.config import CONFIG_LOADER, get_config

AioPikaInstrumentor().instrument()

CONFIG_LOADER.load_config(
    config_path="tests/test_configs/test_config_mongo.yaml",
    secrets_path="tests/test_configs/test_secrets.yaml",
)

config = get_config()
admin_database = admin_database_factory(config.admin_database)
private_credentials = config.private_db_credentials
set_opendp_features_config(config.dp_libraries.opendp)

# TODO: merge in pydantic-settings
amqp_user = os.environ.get("LOMAS_AMQP_USER", "guest")
amqp_pass = os.environ.get("LOMAS_AMQP_PASS", "guest")


def handle_known_exceptions(exc):
    """Transform KNOWN_EXCEPTIONS into a status_code and message for serialization."""

    match exc:
        case ExternalLibraryException():
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content=jsonable_encoder(
                    ExternalLibraryExceptionModel(message=exc.error_message, library=exc.library)
                ),
            )
        case InternalServerException():
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=jsonable_encoder(InternalServerExceptionModel()),
            )
        case InvalidQueryException():
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=jsonable_encoder(InvalidQueryExceptionModel(message=exc.error_message)),
            )
        case UnauthorizedAccessException():
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=jsonable_encoder(UnauthorizedAccessExceptionModel(message=exc.error_message)),
            )


def handle_cost_query(body):
    """Handle Cost query into CostResponse."""

    start_sec = time.time()
    message = body.decode()
    _, dp_library, request_model = message.split(":", 2)

    match dp_library:
        case DPLibraries.SMARTNOISE_SQL:
            request_model = SmartnoiseSQLRequestModel.model_validate_json(request_model)

        case DPLibraries.SMARTNOISE_SYNTH:
            request_model = SmartnoiseSynthRequestModel.model_validate_json(request_model)

        case DPLibraries.OPENDP:
            request_model = OpenDPRequestModel.model_validate_json(request_model)

        case DPLibraries.DIFFPRIVLIB:
            request_model = DiffPrivLibRequestModel.model_validate_json(request_model)
    try:
        data_connector = data_connector_factory(
            request_model.dataset_name,
            admin_database,
            private_credentials,
        )

        dp_querier = querier_factory(
            dp_library,
            data_connector=data_connector,
            admin_database=admin_database,
        )

        eps_cost, delta_cost = dp_querier.cost(request_model)
        elapsed = time.time() - start_sec
        logging.info(f" [x] Done ({elapsed:.2f})")
        return CostResponse(epsilon=eps_cost, delta=delta_cost)
    except KNOWN_EXCEPTIONS as exc:
        known_exc = handle_known_exceptions(exc)
        logging.info(f" [-] KNOWN_EXCEPTIONS ({known_exc.status_code}|{known_exc.body})")
        return known_exc.body, known_exc.status_code


def handle_query(body):
    """Handle DP query into QueryResponse."""

    start_sec = time.time()
    message = body.decode()
    user_name, dp_library, query_json = message.split(":", 2)

    match dp_library:
        case DPLibraries.SMARTNOISE_SQL:
            query_json = SmartnoiseSQLQueryModel.model_validate_json(query_json)

        case DPLibraries.SMARTNOISE_SYNTH:
            query_json = SmartnoiseSynthQueryModel.model_validate_json(query_json)

        case DPLibraries.OPENDP:
            query_json = OpenDPQueryModel.model_validate_json(query_json)

        case DPLibraries.DIFFPRIVLIB:
            query_json = DiffPrivLibQueryModel.model_validate_json(query_json)

    try:
        data_connector = data_connector_factory(
            query_json.dataset_name,
            admin_database,
            private_credentials,
        )

        dp_querier = querier_factory(
            dp_library,
            data_connector=data_connector,
            admin_database=admin_database,
        )
        query_response = dp_querier.handle_query(query_json, user_name)
        elapsed = time.time() - start_sec
        logging.info(f" [x] Done ({elapsed:.2f})")
        return query_response
    except KNOWN_EXCEPTIONS as exc:
        known_exc = handle_known_exceptions(exc)
        logging.info(f" [-] KNOWN_EXCEPTIONS ({known_exc.status_code}|{known_exc.body})")
        return known_exc.body, known_exc.status_code


def handle_dummy_query(body):
    """Handle DP-dummy query into QueryResponse."""

    start_sec = time.time()
    message = body.decode()
    user_name, dp_library, query_model = message.split(":", 2)

    match dp_library:
        case DPLibraries.SMARTNOISE_SQL:
            query_model = SmartnoiseSQLDummyQueryModel.model_validate_json(query_model)
        case DPLibraries.SMARTNOISE_SYNTH:
            query_model = SmartnoiseSynthDummyQueryModel.model_validate_json(query_model)
        case DPLibraries.OPENDP:
            query_model = OpenDPDummyQueryModel.model_validate_json(query_model)
        case DPLibraries.DIFFPRIVLIB:
            query_model = DiffPrivLibDummyQueryModel.model_validate_json(query_model)

    try:
        data_connector = get_dummy_dataset_for_query(admin_database, query_model)
        dummy_querier = querier_factory(
            dp_library,
            data_connector=data_connector,
            admin_database=admin_database,
        )
        eps_cost, delta_cost = dummy_querier.cost(query_model)
        result = dummy_querier.query(query_model)
        dummy_query_response = QueryResponse(
            requested_by=user_name, result=result, epsilon=eps_cost, delta=delta_cost
        )
        elapsed = time.time() - start_sec
        logging.info(f" [x] Done ({elapsed:.2f})")
        return dummy_query_response
    except KNOWN_EXCEPTIONS as exc:
        known_exc = handle_known_exceptions(exc)
        logging.info(f" [-] KNOWN_EXCEPTIONS ({known_exc.status_code}|{known_exc.body})")
        return known_exc.body, known_exc.status_code


async def process_message(channel, in_queue, out_queue, message_handler):
    """General RabbitMQ Message handler -> processing -> response."""

    queue = await channel.declare_queue(in_queue, auto_delete=True)
    await channel.declare_queue(out_queue, auto_delete=True)

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                headers = None
                body = bytes()

                match message_handler(message.body):
                    case (bytes(exc_body), int(status_code)):
                        headers = {"type": "exception", "status_code": status_code}
                        body = exc_body

                    case query_response:
                        logging.info("Response length: {len(query_response.json())} {message.correlation_id}")
                        body = query_response.json().encode()

                await channel.default_exchange.publish(
                    aio_pika.Message(headers=headers, body=body, correlation_id=message.correlation_id),
                    routing_key=out_queue,
                )


class TerminateTaskGroup(Exception):
    """Exception raised to terminate a task group."""


async def force_terminate_task_group():
    """Used to force termination of a task group."""
    raise TerminateTaskGroup()


def ask_exit(signame, tg):
    """Signal handler for TaskGroup termination."""

    logging.info(f"got signal {signame}: exit")
    tg.create_task(force_terminate_task_group())


async def process_all_queues():
    """Handle & await all pika processing queues."""

    loop = asyncio.get_running_loop()
    connection = await aio_pika.connect_robust(f"amqp://{amqp_user}:{amqp_pass}@127.0.0.1/")

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        try:
            async with asyncio.TaskGroup() as tg:
                tg.create_task(process_message(channel, "task_queue", "task_response", handle_query))
                tg.create_task(process_message(channel, "cost_queue", "cost_response", handle_cost_query))
                tg.create_task(process_message(channel, "dummy_queue", "dummy_response", handle_dummy_query))

                # register signal for polite TaskGroup termination
                for signame in ["SIGINT", "SIGTERM"]:
                    loop.add_signal_handler(
                        getattr(signal, signame), functools.partial(ask_exit, signame, tg)
                    )
            # All tasks in Taskgroup are awaited here (aexit of TaskGroup context)
        except* TerminateTaskGroup:
            logging.info("Terminated")
        finally:
            await channel.close()
            await connection.close()


if __name__ == "__main__":
    if TELEMETRY:
        LoggingInstrumentor().instrument(set_logging_format=True)
        init_telemetry(get_ressource(SERVER_SERVICE_NAME, SERVICE_ID))

    logging.info(" [*] Waiting for messages. To exit press CTRL+C")
    asyncio.run(process_all_queues())

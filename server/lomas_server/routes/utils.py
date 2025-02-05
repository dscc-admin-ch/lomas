import asyncio
import os
import random
import time
from contextlib import asynccontextmanager
from functools import wraps

import aio_pika
from fastapi import Request
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    InternalServerException,
    UnauthorizedAccessException,
)
from lomas_core.models.requests import (
    DummyQueryModel,
    LomasRequestModel,
    QueryModel,
)
from lomas_core.models.responses import CostResponse, Job, QueryResponse
from lomas_server.utils.config import get_config

AioPikaInstrumentor().instrument()

# TODO: merge in pydantic-settings
amqp_user = os.environ.get("LOMAS_AMQP_USER", "guest")
amqp_pass = os.environ.get("LOMAS_AMQP_PASS", "guest")


async def process_response(queue, cls, jobs_var):
    """Process responses queue into Jobs."""

    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                jobs = jobs_var.get()

                match message.headers:
                    case {"type": "exception", "status_code": status_code}:
                        jobs[message.correlation_id].error = message.body.decode()
                        jobs[message.correlation_id].status = "failed"
                        jobs[message.correlation_id].result = None
                        jobs[message.correlation_id].status_code = status_code
                    case _:
                        jobs[message.correlation_id].result = cls.model_validate_json(message.body.decode())
                        jobs[message.correlation_id].status = "complete"

                jobs_var.set(jobs)


@asynccontextmanager
async def rabbitmq_ctx(app):
    """RabbitMQ queue context to connect and register callbacks."""

    connection = await aio_pika.connect_robust(f"amqp://{amqp_user}:{amqp_pass}@127.0.0.1/")
    channel = await connection.channel()

    await channel.declare_queue("task_queue", auto_delete=True)
    app.state.task_queue_channel = channel
    queue = await channel.declare_queue("task_response", auto_delete=True)
    asyncio.create_task(process_response(queue, QueryResponse, app.state.jobs_var))

    await channel.declare_queue("cost_queue", auto_delete=True)
    app.state.cost_queue_channel = channel
    queue = await channel.declare_queue("cost_response", auto_delete=True)
    asyncio.create_task(process_response(queue, CostResponse, app.state.jobs_var))

    await channel.declare_queue("dummy_queue", auto_delete=True)
    app.state.dummy_queue_channel = channel
    queue = await channel.declare_queue("dummy_response", auto_delete=True)
    asyncio.create_task(process_response(queue, QueryResponse, app.state.jobs_var))

    yield  # lomas_app is handling requests

    await connection.close()


def timing_protection(func):
    """Adds delays to requests response to protect against timing attack."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        response = func(*args, **kwargs)
        process_time = time.time() - start_time

        config = get_config()
        if config.server.time_attack:
            match config.server.time_attack.method:
                case "stall":
                    # Slows to a minimum response time defined by magnitude
                    if process_time < config.server.time_attack.magnitude:
                        time.sleep(config.server.time_attack.magnitude - process_time)
                case "jitter":
                    # Adds some time between 0 and magnitude secs
                    time.sleep(config.server.time_attack.magnitude * random.uniform(0, 1))
                case _:
                    raise InternalServerException("Time attack method not supported.")
        return response

    return wrapper


@timing_protection
async def handle_query_on_private_dataset(
    request: Request,
    query_json: QueryModel,
    user_name: str,
    dp_library: DPLibraries,
) -> Job:
    """
    Handles queries on private datasets for all supported libraries.

    Args:
        request (Request): Raw request object
        query_model (DummyQueryModel): An instance of DummyQueryModel,
            specific to the library.
        user_name (str): The user name
        dp_library (DPLibraries): Name of the DP library to use for the request

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        Job: A scheduled Job resulting in a QueryResponse containing the result of the query
            (specific to the library) as well as the cost of the query.
    """
    app = request.app

    new_task = Job()

    jobs = app.state.jobs_var.get()
    jobs[str(new_task.uid)] = new_task
    app.state.jobs_var.set(jobs)

    await app.state.task_queue_channel.default_exchange.publish(
        aio_pika.Message(
            body=f"{user_name}:{dp_library}:{query_json.json()}".encode(), correlation_id=new_task.uid
        ),
        routing_key="task_queue",
    )

    return new_task


async def handle_query_on_dummy_dataset(
    request: Request,
    query_model: DummyQueryModel,
    user_name: str,
    dp_library: DPLibraries,
) -> Job:
    """
    Handles queries on dummy datasets for all supported libraries.

    Args:
        request (Request): Raw request object
        query_model (DummyQueryModel): An instance of DummyQueryModel,
            specific to the library.
        user_name (str): The user name
        dp_library (DPLibraries): Name of the DP library to use for the request

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        Job: A scheduled Job resulting in a QueryResponse containing the result of the query
            (specific to the library) as well as the cost of such a query if it was
            executed on a private dataset.
    """
    app = request.app

    dataset_name = query_model.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(user_name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_name} does not have access to {dataset_name}.",
        )

    new_task = Job()

    jobs = app.state.jobs_var.get()
    jobs[str(new_task.uid)] = new_task
    app.state.jobs_var.set(jobs)

    await app.state.dummy_queue_channel.default_exchange.publish(
        aio_pika.Message(
            body=f"{user_name}:{dp_library}:{query_model.json()}".encode(), correlation_id=new_task.uid
        ),
        routing_key="dummy_queue",
    )

    return new_task


@timing_protection
async def handle_cost_query(
    request: Request,
    request_model: LomasRequestModel,
    user_name: str,
    dp_library: DPLibraries,
) -> Job:
    """
    Handles cost queries for DP libraries.

    Args:
        request (Request): Raw request object
        request_model (LomasRequestModel): An instance of LomasRequestModel,
            specific to the library.
        user_name (str): The user name
        dp_library (DPLibraries): Name of the DP library to use for the request

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        Job: A scheduled Job resulting in a CostResponse containing the epsilon, delta and
            privacy-loss budget cost for the request.
    """
    app = request.app

    dataset_name = request_model.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(user_name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_name} does not have access to {dataset_name}.",
        )

    new_task = Job()

    jobs = app.state.jobs_var.get()
    jobs[str(new_task.uid)] = new_task
    app.state.jobs_var.set(jobs)

    await app.state.cost_queue_channel.default_exchange.publish(
        aio_pika.Message(
            body=f"{user_name}:{dp_library}:{request_model.json()}".encode(), correlation_id=new_task.uid
        ),
        routing_key="cost_queue",
    )

    return new_task

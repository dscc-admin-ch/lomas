import asyncio
import os
import random
import time
from contextlib import asynccontextmanager
from functools import wraps
from typing import Annotated

import aio_pika
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import UnauthorizedAccessException
from lomas_core.error_handler import (
    KNOWN_EXCEPTIONS,
    InternalServerException,
    UnauthorizedAccessException,
)
from lomas_core.models.collections import UserId
from lomas_core.models.constants import TimeAttackMethod
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

    yield  # app is handling requests

    await connection.close()


def timing_protection(func):
    """Adds delays to requests response to protect against timing attack."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        config = get_config()

        start_time = time.time()
        response = func(*args, **kwargs)
        process_time = time.time() - start_time

        match config.server.time_attack.method:
            case TimeAttackMethod.STALL:
                # Slows to a minimum response time defined by magnitude
                if process_time < config.server.time_attack.magnitude:
                    time.sleep(config.server.time_attack.magnitude - process_time)
            case TimeAttackMethod.JITTER:
                # Adds some time between 0 and magnitude secs
                time.sleep(config.server.time_attack.magnitude * random.uniform(0, 1))
        return response

    return wrapper


def get_user_id_from_authenticator(
    request: Request,
    security_scopes: SecurityScopes,
    auth_creds: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
) -> UserId:
    """Extracts the authenticator from the app state and calls its get_user_id method.

    Also adds the user_name to the request state to annotate the telemetry request span.

    Args:
        request (Request): The request to access the app and state.
        auth_creds (Annotated[HTTPAuthorizationCredentials, Depends): The HTTP bearer token.

    Returns:
        UserId: A UserId instance extracted from the token.
    """
    user_id = request.app.state.authenticator.get_user_id(security_scopes, auth_creds)
    request.state.user_name = user_id.name
    
    return user_id


@timing_protection
async def handle_query_to_job(
    request: Request,
    query: DummyQueryModel | QueryModel | LomasRequestModel,
    user_name: str,
    dp_library: DPLibraries,
) -> Job:
    """
    Submit Job to handles queries on private, dummy and cost datasets on a worker.

    Args:
        request (Request): Raw request object
        query (DummyQueryModel|QueryModel|LomasRequestModel): A Request or Query to be scheduled
        user_name (str): The user name
        dp_library (DPLibraries): Name of the DP library to use for the request

    Raises:
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        Job: A scheduled Job resulting in a QueryResponse containing the result of the query
            (specific to the library) as well as the cost of the query.
            or a CostResponse containing the epsilon, delta and privacy-loss budget cost for the request.
    """
    app = request.app

    dataset_name = query.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(user_name, dataset_name):
        raise UnauthorizedAccessException(f"{user_name} does not have access to {dataset_name}.")

    match query:
        case DummyQueryModel():
            queue_name = "dummy_queue"
        case QueryModel():
            queue_name = "task_queue"
        case LomasRequestModel():
            queue_name = "cost_queue"

    new_task = Job()

    jobs = app.state.jobs_var.get()
    jobs[str(new_task.uid)] = new_task
    app.state.jobs_var.set(jobs)

    await app.state.cost_queue_channel.default_exchange.publish(
        aio_pika.Message(
            body=f"{user_name}:{dp_library}:{query.json()}".encode(), correlation_id=new_task.uid
        ),
        routing_key=queue_name,
    )

    return new_task

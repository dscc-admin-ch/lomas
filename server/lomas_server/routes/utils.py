import asyncio
import posix as Status
import random
import sys
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import wraps
from typing import Annotated
from uuid import UUID

import aio_pika
from aio_pika.patterns import RPC
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes
from opentelemetry.instrumentation.aio_pika import AioPikaInstrumentor

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    InternalServerException,
    UnauthorizedAccessException,
)
from lomas_core.models.collections import DSPathAccess, DSS3Access, UserId
from lomas_core.models.constants import PrivateDatabaseType, TimeAttackMethod, init_logging
from lomas_core.models.exceptions import LomasServerExceptionTypeAdapter
from lomas_core.models.requests import (
    DummyQueryModel,
    LomasRequestModel,
    QueryModel,
)
from lomas_core.models.responses import CostResponse, Job, QueryResponse
from lomas_server.auth.auth import get_user_id
from lomas_server.data_connector.path_connector import PathConnector
from lomas_server.data_connector.s3_connector import S3Connector
from lomas_server.models.config import Config, PrivateDBCredentials, S3CredentialsConfig

logger = init_logging(__name__)

AioPikaInstrumentor().instrument()


async def process_response(
    queue: aio_pika.Queue, cls: type[QueryResponse | CostResponse], jobs: dict[UUID, Job]
) -> None:
    """Process responses queue into Jobs."""
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process(ignore_processed=True):
                if message.correlation_id not in jobs:
                    await message.reject(requeue=True)
                else:
                    await message.ack()

                    message_body = message.body.decode()
                    match message.headers:
                        case {"type": "exception", "status_code": status_code}:
                            jobs[
                                message.correlation_id
                            ].error = LomasServerExceptionTypeAdapter.validate_json(message_body)
                            jobs[message.correlation_id].status = "failed"
                            jobs[message.correlation_id].result = None
                            jobs[message.correlation_id].status_code = status_code
                        case _:
                            jobs[message.correlation_id].result = cls.model_validate_json(message_body)
                            jobs[message.correlation_id].status = "complete"


async def rabbitmq_connect_queue(
    config: Config, reconnect_interval: int = 10, timeout: int = 120
) -> aio_pika.RobustConnection:
    """Attempt with retries to connect to the queue."""
    try:
        async with asyncio.timeout(timeout):
            connection = await aio_pika.connect_robust(
                str(config.amqp.dsn),
                fail_fast=False,
                reconnect_interval=reconnect_interval,
            )
            return connection
    except TimeoutError:
        logger.error(f"Couldn't connect to queue {config.amqp.base_url} in time")
        sys.exit(Status.EX_UNAVAILABLE)


@asynccontextmanager
async def rabbitmq_ctx(app: FastAPI) -> AsyncIterator[None]:
    """RabbitMQ queue context to connect and register callbacks."""
    config = Config()

    connection = await rabbitmq_connect_queue(config)
    channel = await connection.channel()
    background_tasks = set()  # Avoid dangling asyncio.Task by storing them here

    await channel.declare_queue("task_queue", auto_delete=True)
    app.state.task_queue_channel = channel
    queue = await channel.declare_queue("task_response", auto_delete=True)
    tasks_response_task = asyncio.create_task(process_response(queue, QueryResponse, app.state.jobs))
    background_tasks.add(tasks_response_task)
    tasks_response_task.add_done_callback(background_tasks.discard)

    await channel.declare_queue("cost_queue", auto_delete=True)
    app.state.cost_queue_channel = channel
    queue = await channel.declare_queue("cost_response", auto_delete=True)
    cost_response_task = asyncio.create_task(process_response(queue, CostResponse, app.state.jobs))
    background_tasks.add(cost_response_task)
    cost_response_task.add_done_callback(background_tasks.discard)

    await channel.declare_queue("dummy_queue", auto_delete=True)
    app.state.dummy_queue_channel = channel
    queue = await channel.declare_queue("dummy_response", auto_delete=True)
    dummy_response_task = asyncio.create_task(process_response(queue, QueryResponse, app.state.jobs))
    background_tasks.add(dummy_response_task)
    dummy_response_task.add_done_callback(background_tasks.discard)

    rpc = await RPC.create(channel)
    await rpc.register("get_and_set_may_user_query", app.state.admin_database.get_and_set_may_user_query)
    await rpc.register("set_may_user_query", app.state.admin_database.set_may_user_query)
    await rpc.register("get_remaining_budget", app.state.admin_database.get_remaining_budget)
    await rpc.register("update_budget", app.state.admin_database.update_budget)
    await rpc.register("save_query", app.state.admin_database.save_query)
    await rpc.register("get_dataset_metadata", app.state.admin_database.get_dataset_metadata)

    yield  # app is handling requests

    await connection.close()


def timing_protection(func):  # type: ignore[no-untyped-def]
    """Adds delays to requests response to protect against timing attack."""

    @wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        config = Config()

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
        security_scopes (SecurityScopes): The required scopes for the endpoint.
        auth_creds (Annotated[HTTPAuthorizationCredentials, Depends): The HTTP bearer token.

    Returns:
        UserId: A UserId instance extracted from the token.
    """
    user_id = get_user_id(request.app.state.authenticator, security_scopes, auth_creds)
    request.state.user_name = user_id.name

    return user_id


def get_dataset_credentials(
    private_db_credentials: dict[int, PrivateDBCredentials],
    db_type: PrivateDatabaseType,
    credentials_name: str,
) -> PrivateDBCredentials:
    """
    Search the list of private database credentials and.

    returns the one that matches the database type and
    credentials name.

    Args:
        private_db_credentials (Sequence[PrivateDBCredentials]):\
            The list of private database credentials.
        db_type (PrivateDatabaseType): The type of the database.

    Raises:
        InternalServerException: If the credentials are not found.

    Returns:
        PrivateDBCredentials: The matching credentials.
    """
    if db_type == PrivateDatabaseType.S3:
        for c in private_db_credentials.values():
            if isinstance(c, S3CredentialsConfig) and (credentials_name == c.credentials_name):
                return c

    raise InternalServerException(
        "Could not find credentials for private dataset. Please contact server administrator."
    )


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
    admin_database = app.state.admin_database
    private_db_credentials = app.state.private_db_credentials

    dataset_name = query.dataset_name

    if not admin_database.has_user_access_to_dataset(user_name, dataset_name):
        raise UnauthorizedAccessException(f"{user_name} does not have access to {dataset_name}.")

    ds_access = admin_database.get_dataset(dataset_name).dataset_access
    ds_metadata = admin_database.get_dataset_metadata(dataset_name)
    data_connector = None

    match ds_access:
        case DSPathAccess():
            data_connector = PathConnector(metadata=ds_metadata, dataset_path=ds_access.path)
        case DSS3Access():
            credentials = get_dataset_credentials(
                private_db_credentials,
                ds_access.database_type,
                ds_access.credentials_name,
            )

            if not isinstance(credentials, S3CredentialsConfig):
                raise InternalServerException("Could not get correct credentials")

            ds_access = DSS3Access.model_validate(ds_access)
            ds_access.access_key_id = credentials.access_key_id
            ds_access.secret_access_key = credentials.secret_access_key

            data_connector = S3Connector(metadata=ds_metadata, credentials=ds_access)
        case _:
            raise InternalServerException(f"Unknown database type: {ds_access.database_type}")

    match query:
        case DummyQueryModel():
            queue_name = "dummy_queue"
        case QueryModel():
            queue_name = "task_queue"
        case LomasRequestModel():
            queue_name = "cost_queue"

    new_task = Job(requested_by=user_name)

    app.state.jobs[str(new_task.uid)] = new_task

    await app.state.cost_queue_channel.default_exchange.publish(
        aio_pika.Message(
            body=f"{user_name}λ{dp_library}λ{data_connector.model_dump_json()}λ{query.model_dump_json()}".encode(),
            correlation_id=new_task.uid,
        ),
        routing_key=queue_name,
    )

    return new_task

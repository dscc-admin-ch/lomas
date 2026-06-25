import asyncio
import posix as Status
import random
import sys
import time
from collections.abc import AsyncIterator, Coroutine
from contextlib import asynccontextmanager
from functools import wraps
from pathlib import Path
from typing import Annotated
from uuid import UUID

import aio_pika
from aio_pika.abc import AbstractConnection, AbstractQueue
from aio_pika.patterns import RPC
from fastapi import Depends, FastAPI, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes
from starlette import status

from lomas_core.constants import DPLibraries
from lomas_core.exceptions import (
    InternalServerException,
    UnauthorizedAccessException,
)
from lomas_core.models.collections import DSPathAccess, DSS3Access, UserId
from lomas_core.models.constants import PrivateDatabaseType, TimeAttackMethod, get_lomas_logger
from lomas_core.models.exceptions import LomasAPIErrorModel
from lomas_core.models.requests import (
    DummyQueryModel,
    LomasRequestModel,
    QueryModel,
)
from lomas_core.models.responses import CostResponse, Job, QueryResponse
from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.auth.auth import authorize_user
from lomas_server.data_connector.path_connector import PathConnector
from lomas_server.data_connector.s3_connector import S3Connector
from lomas_server.models.config import Config, PrivateDBCredentials, S3CredentialsConfig

logger = get_lomas_logger(__name__)


async def process_response(
    queue: AbstractQueue, cls: type[QueryResponse | CostResponse], admin_database: AdminDatabase
) -> None:
    """Process responses from queues into Jobs."""
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            try:
                async with message.process(ignore_processed=True):
                    try:
                        if not admin_database.does_job_exist(UUID(message.correlation_id)):
                            await message.reject(requeue=True)
                        else:
                            await message.ack()

                            message_body = message.body.decode()
                            match message.headers:
                                case {"type": "exception", "status_code": int() as status_code}:
                                    logger.debug(message_body)
                                    updated_job = Job(
                                        uid=UUID(message.correlation_id),
                                        status="failed",
                                        error=LomasAPIErrorModel.model_validate_json(message_body),
                                        result=None,
                                        status_code=status_code,
                                    )
                                    admin_database.update_job(updated_job)
                                case _:
                                    updated_job = Job(
                                        uid=UUID(message.correlation_id),
                                        result=cls.model_validate_json(message_body),
                                        status="complete",
                                    )
                                    admin_database.update_job(updated_job)
                    except Exception as e:
                        # Fail the job if we cannot parse worker responses
                        logger.exception("Could not parse worker response.")
                        updated_job = Job(
                            uid=UUID(message.correlation_id),
                            status="failed",
                            error=LomasAPIErrorModel(
                                message="InternalServerException: Could not parse response from worker."
                            ),
                            result=None,
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )
                        admin_database.update_job(updated_job)
                        raise InternalServerException("Could not parse worker response.") from e
            except Exception as e:
                # TODO is this right? -> ignore this message and proceed as if nothing happened?
                logger.exception("Error while handling worker responses, continuuing...")
                raise InternalServerException from e


async def rabbitmq_connect_queue(
    config: Config, reconnect_interval: int = 10, timeout: int = 120
) -> AbstractConnection:
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
    background_tasks = set()  # Avoid dangling asyncio.Task by storing them here

    # Setting things up
    try:
        # Rabbit connection and single channel
        connection = await rabbitmq_connect_queue(config)
        channel = await connection.channel()

        # Queues
        await channel.declare_queue("task_queue", durable=True)
        app.state.task_queue_channel = channel
        queue = await channel.declare_queue("task_response", durable=True)

        await channel.declare_queue("cost_queue", durable=True)
        app.state.cost_queue_channel = channel
        cost_queue = await channel.declare_queue("cost_response", durable=True)

        await channel.declare_queue("dummy_queue", durable=True)
        app.state.dummy_queue_channel = channel
        dummy_queue = await channel.declare_queue("dummy_response", durable=True)

        # Rpc stuff
        rpc = await RPC.create(channel, durable=True)
        await rpc.register(
            "get_and_set_may_user_query", app.state.admin_database.get_and_set_may_user_query, durable=True
        )
        await rpc.register("set_may_user_query", app.state.admin_database.set_may_user_query, durable=True)
        await rpc.register(
            "get_remaining_budget", app.state.admin_database.get_remaining_budget, durable=True
        )
        await rpc.register("update_budget", app.state.admin_database.update_budget, durable=True)
        await rpc.register("save_query", app.state.admin_database.save_query, durable=True)
        await rpc.register(
            "get_dataset_metadata", app.state.admin_database.get_dataset_metadata, durable=True
        )

    except Exception as e:
        logger.exception(f"Failed to setup RabbitMQ context: {e!s}")
        if connection:
            await connection.close()
        raise InternalServerException("Failed to setup RabbitMQ context") from e

    # Utils
    def on_task_done(task: asyncio.Task) -> None:
        background_tasks.discard(task)  # drop reference

        # Log and raise (server does not work anymore)
        if task.cancelled():
            logger.warning(f"Rabbit task {task.get_name()!r} cancelled")
        elif exc := task.exception():
            logger.exception(f"Exception in rabbit task {task.get_name()!r}.", exc_info=exc)
            raise InternalServerException from exc

    def make_task(coroutine: Coroutine, name: str) -> None:
        task = asyncio.create_task(coroutine, name=name)
        # keep reference and add done callback
        background_tasks.add(task)
        task.add_done_callback(on_task_done)

    # Handlers
    make_task(process_response(queue, QueryResponse, app.state.admin_database), "query_response")
    make_task(process_response(cost_queue, CostResponse, app.state.admin_database), "cost_response")
    make_task(process_response(dummy_queue, QueryResponse, app.state.admin_database), "dummy_response")

    try:
        yield  # app is handling requests
    finally:
        # Cancel background tasks
        for task in background_tasks:
            task.cancel()
        await asyncio.gather(*background_tasks, return_exceptions=True)

        try:
            await connection.close()
        except Exception:
            logger.exception("Error while closing RabbitMQ connection during shutdown")

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
    # Bootstrap initialization
    if not request.app.state.admin_database.get_bootstrap_disabled():
        bootstrap_cred = request.app.state.admin_database.get_bootstrap()
        match auth_creds:
            case HTTPAuthorizationCredentials(scheme="Bearer") if auth_creds.credentials == bootstrap_cred:
                logger.warning("Bootstrap User Bypass")
                user_id = UserId(name="bootstrap", email="boot@strap.com")
                request.state.user_name = user_id.name
                return user_id
            case _:
                pass

    user_id = request.app.state.authenticator.get_user_id(auth_creds.credentials)
    request.state.user_name = user_id.name
    # This raises an exception if authz fails
    authorize_user(user_id, request.app.state.admin_database, security_scopes)

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
            match path := ds_access.path:
                case Path():
                    data_connector = PathConnector(metadata=ds_metadata, dataset_path=path.resolve())
                case _:
                    data_connector = PathConnector(metadata=ds_metadata, dataset_path=path)
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

    # app.state.jobs[str(new_task.uid)] = new_task
    admin_database.put_job(new_task)

    await app.state.cost_queue_channel.default_exchange.publish(
        aio_pika.Message(
            body=f"{user_name}λ{dp_library}λ{data_connector.model_dump_json()}λ{query.model_dump_json()}".encode(),
            correlation_id=new_task.uid,
        ),
        routing_key=queue_name,
    )

    return new_task

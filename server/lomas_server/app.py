import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from concurrent.futures.thread import ThreadPoolExecutor
from contextlib import asynccontextmanager
from contextvars import ContextVar
from uuid import UUID

import aio_pika
from fastapi import Depends, FastAPI, Response
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from lomas_core.error_handler import (
    InternalServerException,
    add_exception_handlers,
)
from lomas_core.instrumentation import get_ressource, init_telemetry
from lomas_core.models.constants import AdminDBType
from lomas_core.models.responses import QueryResponse
from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.admin_database.utils import add_demo_data_to_mongodb_admin
from lomas_server.admin_database.yaml_database import AdminYamlDatabase
from lomas_server.constants import (
    CONFIG_NOT_LOADED,
    DB_NOT_LOADED,
    SERVER_SERVICE_NAME,
    SERVICE_ID,
)
from lomas_server.dp_queries.dp_libraries.opendp import (
    set_opendp_features_config,
)
from lomas_server.routes import routes_admin, routes_dp
from lomas_server.routes.middlewares import (
    FastAPIMetricMiddleware,
    LoggingAndTracingMiddleware,
)
from lomas_server.routes.utils import server_live
from lomas_server.utils.config import get_config

jobs_var: ContextVar = ContextVar("jobs", default={})

# TODO: merge in pydantic-settings
amqp_user = os.environ.get("LOMAS_AMQP_USER", "guest")
amqp_pass = os.environ.get("LOMAS_AMQP_PASS", "guest")


async def process_task_response(queue):
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                print(f"message: {message.body} | HEADERS: {message.headers}")
                jobs = jobs_var.get()

                match message.headers:

                    case {"type": "exception", "status_code": status_code}:
                        exc = message.body.decode()
                        print(exc)
                        jobs[message.correlation_id].status = "failed"
                        jobs[message.correlation_id].result = None
                        jobs[message.correlation_id].error = message.body.decode()
                        jobs[message.correlation_id].status_code = status_code

                    case {"type": "exception"}:
                        exc = message.body.decode()
                        print(exc)
                        jobs[message.correlation_id].status = "failed"
                        jobs[message.correlation_id].result = None

                    case _:
                        jobs[message.correlation_id].status = "complete"
                        jobs[message.correlation_id].result = QueryResponse.model_validate_json(
                            message.body.decode()
                        )

                print(jobs)
                jobs_var.set(jobs)


@asynccontextmanager
async def lifespan(lomas_app: FastAPI) -> AsyncGenerator:
    """
    Lifespan function for the server.

    This function is executed once on server startup, yields and
    finishes running at server shutdown.

    Server initialization is performed (config loading, etc.) and
    the server state is updated accordingly. This can have potential
    side effects on the return values of the "depends"
    functions, which check the server state.
    """
    # Startup
    logging.info("Startup message")

    # Set some app state
    lomas_app.state.admin_database = None

    # General server state, can add fields if need be.
    lomas_app.state.server_state = {
        "state": [],
        "message": [],
    }
    lomas_app.state.server_state["state"].append("Startup event")

    status_ok = True
    # Load config
    try:
        logging.info("Loading config")
        lomas_app.state.server_state["message"].append("Loading config")
        config = get_config()
        lomas_app.state.private_credentials = config.private_db_credentials
    except InternalServerException:
        logging.info("Config could not loaded")
        lomas_app.state.server_state["state"].append(CONFIG_NOT_LOADED)
        lomas_app.state.server_state["message"].append("Server could not be started!")
        lomas_app.state.live = False
        status_ok = False

    # Fill up user database if in develop mode ONLY
    if status_ok and config.develop_mode:
        logging.info("!! Develop mode ON !!")
        lomas_app.state.server_state["message"].append("!! Develop mode ON !!")
        if config.admin_database.db_type == AdminDBType.MONGODB:
            logging.info("Adding demo data to MongoDB Admin")
            lomas_app.state.server_state["message"].append("Adding demo data to MongoDB Admin")
            add_demo_data_to_mongodb_admin()

    # Load admin database
    if status_ok:
        try:
            logging.info("Loading admin database")
            lomas_app.state.server_state["message"].append("Loading admin database")
            lomas_app.state.admin_database = admin_database_factory(config.admin_database)
        except InternalServerException as e:
            logging.exception(f"Failed at startup: {str(e)}")
            lomas_app.state.server_state["state"].append(DB_NOT_LOADED)
            lomas_app.state.server_state["message"].append(f"Admin database could not be loaded: {str(e)}")
            lomas_app.state.live = False
            status_ok = False

        lomas_app.state.server_state["state"].append("Startup completed")
        lomas_app.state.server_state["message"].append("Startup completed")

    # Set DP Libraries config
    set_opendp_features_config(config.dp_libraries.opendp)

    if status_ok:
        lomas_app.state.server_state["message"].append("Server start condition OK")
        lomas_app.state.live = True

    app.state.executor = ThreadPoolExecutor()
    app.state.jobs_var = jobs_var

    connection = await aio_pika.connect_robust(f"amqp://{amqp_user}:{amqp_pass}@127.0.0.1/")
    channel = await connection.channel()
    await channel.declare_queue("task_queue", auto_delete=True)
    app.state.task_queue_channel = channel
    queue = await channel.declare_queue("task_response", auto_delete=True)
    asyncio.create_task(process_task_response(queue))

    yield  # lomas_app is handling requests

    await connection.close()

    app.state.executor.shutdown()

    # Shutdown event
    if isinstance(lomas_app.state.admin_database, AdminYamlDatabase):
        lomas_app.state.admin_database.save_current_database()


# Initalise telemetry
LoggingInstrumentor().instrument(set_logging_format=True)
resource = get_ressource(SERVER_SERVICE_NAME, SERVICE_ID)
init_telemetry(resource)

# This object holds the server object
app = FastAPI(lifespan=lifespan)

# Setting metrics middleware
app.add_middleware(FastAPIMetricMiddleware, app_name=SERVER_SERVICE_NAME)
app.add_middleware(LoggingAndTracingMiddleware)

# Add custom exception handlers
add_exception_handlers(app)

# Instrument the FastAPI app
FastAPIInstrumentor.instrument_app(app)

# Add endpoints
app.include_router(routes_dp.router)
app.include_router(routes_admin.router)


@app.get("/status/{uid}")
async def status_handler(uid: UUID, response: Response):
    if (job := jobs_var.get().get(str(uid))) is not None:
        if job.status == "failed":
            response.status_code = job.status_code
        return job


@app.get("/health/live")
async def health_handler(dependencies=[Depends(server_live)]):
    return

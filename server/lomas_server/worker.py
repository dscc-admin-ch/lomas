import asyncio
import os
import time

import aio_pika
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    KNOWN_EXCEPTIONS,
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
    UnauthorizedAccessException,
)
from lomas_core.models.exceptions import (
    ExternalLibraryExceptionModel,
    InternalServerExceptionModel,
    InvalidQueryExceptionModel,
    UnauthorizedAccessExceptionModel,
)
from lomas_core.models.requests import (
    DiffPrivLibQueryModel,
    OpenDPQueryModel,
    SmartnoiseSQLQueryModel,
    SmartnoiseSynthQueryModel,
)
from lomas_server.admin_database.factory import admin_database_factory
from lomas_server.data_connector.factory import data_connector_factory
from lomas_server.dp_queries.dp_libraries.factory import querier_factory
from lomas_server.dp_queries.dp_libraries.opendp import set_opendp_features_config
from lomas_server.tests.constants import (
    mongo_integration_enabled,
)
from lomas_server.utils.config import CONFIG_LOADER, get_config

if mongo_integration_enabled():
    CONFIG_LOADER.load_config(
        config_path="tests/test_configs/test_config_mongo.yaml",
        secrets_path="tests/test_configs/test_secrets.yaml",
    )
else:
    CONFIG_LOADER.load_config(
        config_path="tests/test_configs/test_config.yaml",
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


def process_query(body):
    print(f" [x] Received {body.decode()}")
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

        case _:
            raise "wtf is this"

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
        print(f" [x] Done ({elapsed:.2f})")
        return query_response
    except KNOWN_EXCEPTIONS as exc:
        known_exc = handle_known_exceptions(exc)
        print(f" [-] KNOWN_EXCEPTIONS ({known_exc.status_code}|{known_exc.body})")
        return known_exc.body, known_exc.status_code
    except Exception as e:
        return e


async def main():
    connection = await aio_pika.connect_robust(f"amqp://{amqp_user}:{amqp_pass}@127.0.0.1/")

    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue = await channel.declare_queue("task_queue", auto_delete=True)
        await channel.declare_queue("task_response", auto_delete=True)

        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    headers = None
                    body = bytes()

                    match query_response := process_query(message.body):
                        case Exception():
                            print(f"Exception: {query_response}")
                            headers = {"type": "exception"}
                            body = str(query_response).encode()

                        case (bytes(body), int(status_code)):
                            headers = {"type": "exception", "status_code": status_code}
                            body = body

                        case None:
                            break

                        case _:
                            print("Response length:", len(query_response.json()), message.correlation_id)
                            body = query_response.json().encode()

                    # print(headers, body)
                    await channel.default_exchange.publish(
                        aio_pika.Message(headers=headers, body=body, correlation_id=message.correlation_id),
                        routing_key="task_response",
                    )

                    if queue.name in message.body.decode():
                        break


if __name__ == "__main__":
    print(" [*] Waiting for messages. To exit press CTRL+C")
    asyncio.run(main())

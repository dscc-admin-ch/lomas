import random
import time
from collections.abc import AsyncGenerator
from functools import wraps

from fastapi import Request

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    KNOWN_EXCEPTIONS,
    InternalServerException,
    UnauthorizedAccessException,
)
from lomas_core.models.requests import (
    DummyQueryModel,
    LomasRequestModel,
    QueryModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse
from lomas_server.data_connector.factory import data_connector_factory
from lomas_server.dp_queries.dp_libraries.factory import querier_factory
from lomas_server.dp_queries.dummy_dataset import get_dummy_dataset_for_query
from lomas_server.utils.config import get_config


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


async def server_live(request: Request) -> AsyncGenerator:
    """
    Checks the server is live and throws an exception otherwise.

    Args:
        request (Request): Raw request

    Raises:
        InternalServerException: If the server is not live.

    Returns:
        AsyncGenerator
    """
    if not request.app.state.server_state["LIVE"]:
        raise InternalServerException(
            "Woops, the server did not start correctly. Contact the administrator of this service.",
        )
    yield


@timing_protection
def handle_query_on_private_dataset(
    request: Request,
    query_json: QueryModel,
    user_name: str,
    dp_library: DPLibraries,
) -> QueryResponse:
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
        QueryResponse: A QueryResponse model containing the result of the query
            (specific to the library) as well as the cost of the query.
    """
    app = request.app

    data_connector = data_connector_factory(
        query_json.dataset_name,
        app.state.admin_database,
        app.state.private_credentials,
    )
    dp_querier = querier_factory(
        dp_library,
        data_connector=data_connector,
        admin_database=app.state.admin_database,
    )
    try:
        response = dp_querier.handle_query(query_json, user_name)
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return response


def handle_query_on_dummy_dataset(
    request: Request,
    query_model: DummyQueryModel,
    user_name: str,
    dp_library: DPLibraries,
) -> QueryResponse:
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
        QueryResponse: A QueryResponse model containing the result of the query
            (specific to the library) as well as the cost of such a query if it was
            executed on a private dataset.
    """
    app = request.app

    dataset_name = query_model.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(user_name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_name} does not have access to {dataset_name}.",
        )

    ds_data_connector = get_dummy_dataset_for_query(app.state.admin_database, query_model)
    dummy_querier = querier_factory(
        dp_library,
        data_connector=ds_data_connector,
        admin_database=app.state.admin_database,
    )

    try:
        eps_cost, delta_cost = dummy_querier.cost(query_model)
        result = dummy_querier.query(query_model)
        response = QueryResponse(requested_by=user_name, result=result, epsilon=eps_cost, delta=delta_cost)
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return response


@timing_protection
def handle_cost_query(
    request: Request,
    request_model: LomasRequestModel,
    user_name: str,
    dp_library: DPLibraries,
) -> CostResponse:
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
        CostResponse: A cost response containing the epsilon and delta
            privacy-loss budget cost for the request.
    """
    app = request.app

    dataset_name = request_model.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(user_name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_name} does not have access to {dataset_name}.",
        )

    data_connector = data_connector_factory(
        request_model.dataset_name,
        app.state.admin_database,
        app.state.private_credentials,
    )
    dp_querier = querier_factory(
        dp_library,
        data_connector=data_connector,
        admin_database=app.state.admin_database,
    )
    try:
        eps_cost, delta_cost = dp_querier.cost(request_model)
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return CostResponse(epsilon=eps_cost, delta=delta_cost)

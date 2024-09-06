from collections.abc import AsyncGenerator

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from lomas_server.constants import DPLibraries
from lomas_server.data_connector.factory import data_connector_factory
from lomas_server.dp_queries.dp_libraries.factory import querier_factory
from lomas_server.dp_queries.dummy_dataset import get_dummy_dataset_for_query
from lomas_server.utils.error_handler import (
    KNOWN_EXCEPTIONS,
    InternalServerException,
    UnauthorizedAccessException,
)


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
            "Woops, the server did not start correctly."
            + "Contact the administrator of this service.",
        )
    yield


def handle_query_on_data_connector(
    request: Request,
    query_json: BaseModel,
    user_name: str,
    dp_library: DPLibraries,
):
    """
    Handles queries for the SmartNoiseSQL library.

    Args:
        request (Request): Raw request object
        query_json (BaseModel): A JSON object containing the user request
        user_name (str): The user name
        dp_library: Name of the DP library to use for the query

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        JSONResponse: A JSON object containing the following:
            - requested_by (str): The user name.
            - query_response (pd.DataFrame): A DataFrame containing
              the query response.
            - spent_epsilon (float): The amount of epsilon budget spent
              for the query.
            - spent_delta (float): The amount of delta budget spent
              for the query.
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
    query_json: BaseModel,
    user_name: str,
    dp_library: DPLibraries,
):
    """
    Handles queries for the SmartNoiseSQL library.

    Args:
        request (Request): Raw request object
        query_json (BaseModel): A JSON object containing the user request
        user_name (str): The user name
        dp_library: Name of the DP library to use for the query

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.

    Returns:
        JSONResponse: A JSON object containing the query response.
    """
    app = request.app

    dataset_name = query_json.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(
        user_name, dataset_name
    ):
        raise UnauthorizedAccessException(
            f"{user_name} does not have access to {dataset_name}.",
        )

    ds_data_connector = get_dummy_dataset_for_query(
        app.state.admin_database, query_json
    )
    dummy_querier = querier_factory(
        dp_library,
        data_connector=ds_data_connector,
        admin_database=app.state.admin_database,
    )

    try:
        _ = dummy_querier.cost(query_json)  # verify cost works
        response_df = dummy_querier.query(query_json)
        response = JSONResponse(content={"query_response": response_df})
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return response


def handle_cost_query(
    request: Request,
    query_json: BaseModel,
    user_name: str,
    dp_library: DPLibraries,
):
    """
    Handles cost queries for DP libraries.

    Args:
        request (Request): Raw request object
        query_json (BaseModel): A JSON object containing the user request
        user_name (str): The user name
        dp_library: Name of the DP library to use for the query

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.

    Returns:
        JSONResponse: A JSON object containing:
            - epsilon_cost (float): The estimated epsilon cost.
            - delta_cost (float): The estimated delta cost.
    """
    app = request.app

    dataset_name = query_json.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(
        user_name, dataset_name
    ):
        raise UnauthorizedAccessException(
            f"{user_name} does not have access to {dataset_name}.",
        )

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
        eps_cost, delta_cost = dp_querier.cost(query_json)
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return JSONResponse(
        content={"epsilon_cost": eps_cost, "delta_cost": delta_cost}
    )

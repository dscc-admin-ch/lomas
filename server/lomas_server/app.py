from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any, Callable
from types import SimpleNamespace

from fastapi import Body, Depends, FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from admin_database.admin_database import AdminDatabase
from admin_database.utils import database_factory
from constants import AdminDBType, DPLibraries
from dataset_store.utils import dataset_store_factory
from dp_queries.dp_libraries.utils import querier_factory
from dp_queries.dp_logic import QueryHandler
from dp_queries.dummy_dataset import (
    get_dummy_dataset_for_query,
    make_dummy_dataset,
)
from mongodb_admin import (
    add_datasets,
    create_users_collection,
    drop_collection,
)
from utils.anti_timing_att import anti_timing_att
from utils.config import Config, get_config
from utils.error_handler import (
    CUSTOM_EXCEPTIONS,
    InternalServerException,
    add_exception_handlers,
)
from utils.example_inputs import (
    example_dummy_opendp,
    example_dummy_smartnoise_sql,
    example_get_admin_db_data,
    example_get_dummy_dataset,
    example_opendp,
    example_smartnoise_sql,
    example_smartnoise_sql_cost,
)
from utils.input_models import (
    DummyOpenDPInp,
    DummySNSQLInp,
    GetDbData,
    GetDummyDataset,
    OpenDPInp,
    SNSQLInp,
    SNSQLInpCost,
)
from utils.loggr import LOG
from utils.utils import check_start_condition, server_live, stream_dataframe

# Some global variables
# -----------------------------------------------------------------------------
CONFIG: Config = None
ADMIN_DATABASE: AdminDatabase = None
QUERY_HANDLER: QueryHandler = None

# General server state, can add fields if need be.
SERVER_STATE: dict[str, Any] = {
    "state": [],
    "message": [],
    "LIVE": False,
}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    """
    This function is executed once on server startup
    """
    # Startup event
    LOG.info("Startup message")
    global CONFIG
    global QUERY_HANDLER
    global ADMIN_DATABASE

    SERVER_STATE["state"].append("Startup event")

    # Load config here
    LOG.info("Loading config")
    SERVER_STATE["message"].append("Loading config")
    CONFIG = get_config()

    # Fill up user database if in develop mode ONLY
    if CONFIG.develop_mode:
        LOG.info("!! Develop mode ON !!")
        LOG.info("Creating example user collection")

        args = SimpleNamespace(**vars(CONFIG.admin_database))

        LOG.info("Creating user collection")
        args.clean = True
        args.overwrite = True
        args.path = "/data/collections/user_collection.yaml"
        create_users_collection(args)

        LOG.info("Creating datasets and metadata collection")
        args.path = "/data/collections/dataset_collection.yaml"
        args.overwrite_datasets = True
        args.overwrite_metadata = True
        add_datasets(args)

        LOG.info("Empty archives")
        args.collection = "queries_archives"
        drop_collection(args)

    # Load users, datasets, etc..
    LOG.info("Loading admin database")
    SERVER_STATE["message"].append("Loading admin database")
    try:
        ADMIN_DATABASE = database_factory(CONFIG.admin_database)
    except InternalServerException as e:
        LOG.exception("Failed at startup:" + str(e))
        SERVER_STATE["state"].append("Loading user database at Startup failed")
        SERVER_STATE["message"].append(str(e))

    LOG.info("Loading query handler")
    SERVER_STATE["message"].append("Loading dataset store")
    dataset_store = dataset_store_factory(CONFIG.dataset_store, ADMIN_DATABASE)

    SERVER_STATE["message"].append("Loading query handler")
    QUERY_HANDLER = QueryHandler(ADMIN_DATABASE, dataset_store)

    SERVER_STATE["state"].append("Startup completed")
    SERVER_STATE["message"].append("Startup completed")

    # Finally check everything in startup went well and update the state
    check_start_condition()

    yield  # app is handling requests

    # Shutdown event
    if CONFIG.admin_database.db_type == AdminDBType.YAML_TYPE:
        ADMIN_DATABASE.save_current_database()


# This object holds the server object
app = FastAPI(lifespan=lifespan)


# A simple hack to hinder the timing attackers
@app.middleware("http")
async def middleware(
    request: Request, call_next: Callable[[Request], Response]
) -> Response:
    return await anti_timing_att(request, call_next, CONFIG)


# Add custom exception handlers
add_exception_handlers(app)

# API Endpoints
# -----------------------------------------------------------------------------


# Get server state
@app.get("/state", tags=["ADMIN_USER"])
async def get_state(
    user_name: str = Header(None),
) -> JSONResponse:
    """Returns the current state dict of this server instance.

    Args:
        user_name (str, optional): The user name. Defaults to Header(None).

    Returns:
        JSONResponse: The state of the server instance.
    """
    return JSONResponse(
        content={
            "requested_by": user_name,
            "state": SERVER_STATE,
        }
    )


# Metadata query
@app.post(
    "/get_dataset_metadata",
    dependencies=[Depends(server_live)],
    tags=["USER_METADATA"],
)
def get_dataset_metadata(
    query_json: GetDbData = Body(example_get_admin_db_data),
) -> JSONResponse:
    """
    ```
    Retrieves metadata for a given dataset.

    Args:
        query_json (GetDbData, optional): A JSON object containing
            the dataset_name key for indicating the dataset.
            Defaults to Body(example_get_admin_db_data).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.

    Returns:
        JSONResponse: The metadata dictionary for the specified
            dataset_name.
    ```
    """
    try:
        ds_metadata = ADMIN_DATABASE.get_dataset_metadata(
            query_json.dataset_name
        )

    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return ds_metadata


# Dummy dataset query
@app.post(
    "/get_dummy_dataset",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def get_dummy_dataset(
    query_json: GetDummyDataset = Body(example_get_dummy_dataset),
) -> StreamingResponse:
    """
    ```
    Generates and returns a dummy dataset.

    Args:
        query_json (GetDummyDataset, optional):
            A JSON object containing the following:
                - nb_rows (int, optional): The number of rows in the
                  dummy dataset (default: 100).
                - seed (int, optional): The random seed for generating
                  the dummy dataset (default: 42).
            Defaults to Body(example_get_dummy_dataset).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.

    Returns:
        StreamingResponse: a pd.DataFrame representing the dummy dataset.
    ```
    """
    try:
        ds_metadata = ADMIN_DATABASE.get_dataset_metadata(
            query_json.dataset_name
        )

        dummy_df = make_dummy_dataset(
            ds_metadata, query_json.dummy_nb_rows, query_json.dummy_seed
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return stream_dataframe(dummy_df)


# Smartnoise SQL query
@app.post(
    "/smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def smartnoise_sql_handler(
    query_json: SNSQLInp = Body(example_smartnoise_sql),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    ```
    Handles queries for the SmartNoiseSQL library.

    Args:
        query_json (SNSQLInp): A JSON object containing:
            - query: The SQL query to execute. NOTE: the table name is `df`,
              the query must end with "FROM df".
            - epsilon (float): Privacy parameter (e.g., 0.1).
            - delta (float): Privacy parameter (e.g., 1e-5).
            - mechanisms (dict, optional): Dictionary of mechanisms for the
              query (default: {}). See `Smartnoise-SQL mechanisms documentation
              https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms.
            - postprocess (bool, optional): Whether to postprocess the query
              results (default: True).
              See `Smartnoise-SQL postprocessing documentation
              https://docs.smartnoise.org/sql/advanced.html#postprocess.

            Defaults to Body(example_smartnoise_sql).

        user_name (str, optional): The user name.
            Defaults to Header(None).

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
    ```
    """
    try:
        response = QUERY_HANDLER.handle_query(
            DPLibraries.SMARTNOISE_SQL, query_json, user_name
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return response


# Smartnoise SQL Dummy query
@app.post(
    "/dummy_smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_smartnoise_sql_handler(
    query_json: DummySNSQLInp = Body(example_dummy_smartnoise_sql),
) -> JSONResponse:
    """
    ```
    Handles queries on dummy datasets for the SmartNoiseSQL library.

    Args:
        query_json (DummySNSQLInp, optional): A JSON object containing:
            - query: The SQL query to execute. NOTE: the table name is `df`,
              the query must end with "FROM df".
            - epsilon (float): Privacy parameter (e.g., 0.1).
            - delta (float): Privacy parameter (e.g., 1e-5).
            - mechanisms (dict, optional): Dictionary of mechanisms for the
              query (default: {}). See `Smartnoise-SQL mechanisms documentation
              https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms.
            - postprocess (bool, optional): Whether to postprocess the query
              results (default: True).
              See `Smartnoise-SQL postprocessing documentation
              https://docs.smartnoise.org/sql/advanced.html#postprocess.
            - dummy (bool, optional): Whether to use a dummy dataset
              (default: False).
            - nb_rows (int, optional): The number of rows in the dummy dataset
              (default: 100).
            - seed (int, optional): The random seed for generating
              the dummy dataset (default: 42).

            Defaults to Body(example_dummy_smartnoise_sql).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.

    Returns:
        JSONResponse: A JSON object containing:
            - query_response (pd.DataFrame): a DataFrame containing
              the query response.
    ```
    """
    ds_private_dataset = get_dummy_dataset_for_query(
        ADMIN_DATABASE, query_json
    )
    dummy_querier = querier_factory(
        DPLibraries.SMARTNOISE_SQL, private_dataset=ds_private_dataset
    )
    try:
        _ = dummy_querier.cost(query_json)  # verify cost works
        response_df = dummy_querier.query(query_json)
        response = JSONResponse(content={"query_response": response_df})
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return response


@app.post(
    "/estimate_smartnoise_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_smartnoise_cost(
    query_json: SNSQLInpCost = Body(example_smartnoise_sql_cost),
) -> JSONResponse:
    """
    ```
    Estimates the privacy loss budget cost of a SmartNoiseSQL query.

    Args:
        query_json (SNSQLInpCost, optional):
            A JSON object containing the following:
            - query: The SQL query to estimate the cost for.
              NOTE: the table name is `df`, the query must end with "FROM df".
            - epsilon (float): Privacy parameter (e.g., 0.1).
            - delta (float): Privacy parameter (e.g., 1e-5).
            - mechanisms (dict, optional): Dictionary of mechanisms
              for the query (default: {}).
              See `Smartnoise-SQL mechanisms documentation
              https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms.

            Defaults to Body(example_smartnoise_sql_cost).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.

    Returns:
        JSONResponse: A JSON object containing:
            - epsilon_cost (float): The estimated epsilon cost.
            - delta_cost (float): The estimated delta cost.
    ```
    """
    try:
        response = QUERY_HANDLER.estimate_cost(
            DPLibraries.SMARTNOISE_SQL,
            query_json,
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content=response)


@app.post(
    "/opendp_query", dependencies=[Depends(server_live)], tags=["USER_QUERY"]
)
def opendp_query_handler(
    query_json: OpenDPInp = Body(example_opendp),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    ```
    Handles queries for the OpenDP Library.

    Args:
        query_json (OpenDPInp, optional): A JSON object containing the following:
            - opendp_pipeline: The OpenDP pipeline for the query.
            - fixed_delta: If the pipeline measurement is of type
              "ZeroConcentratedDivergence" (e.g. with `make_gaussian`) then it is
              converted to "SmoothedMaxDivergence" with `make_zCDP_to_approxDP`
              (see `opendp measurements documentation
              <https://docs.opendp.org/en/stable/api/python/opendp.combinators.html#opendp.combinators.make_zCDP_to_approxDP>`_). # noqa
              In that case a `fixed_delta` must be provided by the user.

            Defaults to Body(example_opendp).

        user_name (str, optional): The user name.
            Defaults to Header(None).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The pipeline does not contain a "measurement",
            there is not enough budget or the dataset does not exist.
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
    ```
    """
    try:
        response = QUERY_HANDLER.handle_query(
            DPLibraries.OPENDP, query_json, user_name
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content=response)


@app.post(
    "/dummy_opendp_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_opendp_query_handler(
    query_json: DummyOpenDPInp = Body(example_dummy_opendp),
) -> JSONResponse:
    """
    ```
    Handles queries on dummy datasets for the OpenDP library.

    Args:
        query_json (DummyOpenDPInp, optional):
            A JSON object containing the follwing:
            - opendp_pipeline: The OpenDP pipeline for the query.
            - fixed_delta: If the pipeline measurement is of type
              "ZeroConcentratedDivergence" (e.g. with `make_gaussian`) then
              it is converted to "SmoothedMaxDivergence" with
              `make_zCDP_to_approxDP` (see `opendp measurements documentation
              https://docs.opendp.org/en/stable/api/python/opendp.combinators.html#opendp.combinators.make_zCDP_to_approxDP).
              In that case a `fixed_delta` must be provided by the user.
            - dummy (bool, optional): Whether to use a dummy dataset
              (default: False).
            - nb_rows (int, optional): The number of rows
              in the dummy dataset (default: 100).
            - seed (int, optional): The random seed for generating
              the dummy dataset (default: 42).

            Defaults to Body(example_dummy_opendp).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.

    Returns:
        JSONResponse: A JSON object containing:
            - query_response (pd.DataFrame): a DataFrame containing
              the query response.
    ```
    """
    ds_private_dataset = get_dummy_dataset_for_query(
        ADMIN_DATABASE, query_json
    )
    dummy_querier = querier_factory(
        DPLibraries.OPENDP, private_dataset=ds_private_dataset
    )

    try:
        _ = dummy_querier.cost(query_json)  # verify cost works
        response_df = dummy_querier.query(query_json)
        response = {"query_response": response_df}

    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content=response)


@app.post(
    "/estimate_opendp_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_opendp_cost(
    query_json: OpenDPInp = Body(example_opendp),
) -> JSONResponse:
    """
    ```
    Estimates the privacy loss budget cost of an OpenDP query.

    Args:
        query_json (OpenDPInp, optional):
            A JSON object containing the following:
            - `opendp_pipeline`: The OpenDP pipeline for the query.

            Defaults to Body(example_opendp).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist or the
            pipeline does not contain a measurement.

    Returns:
        JSONResponse: A JSON object containing:
            - epsilon_cost (float): The estimated epsilon cost.
            - delta_cost (float): The estimated delta cost.
    ```
    """
    try:
        response = QUERY_HANDLER.estimate_cost(
            DPLibraries.OPENDP,
            query_json,
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content=response)


# MongoDB get initial budget
@app.post(
    "/get_initial_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_initial_budget(
    query_json: GetDbData = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    ```
    Returns the initial budget for a user and dataset.

    Args:
        query_json (GetDbData, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to Body(example_get_admin_db_data).

        user_name (str, optional): The user name.
            Defaults to Header(None).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: The user does not exist or
            the user does not have access to the dataset.
    Returns:
        JSONResponse: a JSON object with:
            - initial_epsilon (float): initial epsilon budget.
            - initial_delta (float): initial delta budget.
    ```
    """
    try:
        initial_epsilon, initial_delta = ADMIN_DATABASE.get_initial_budget(
            user_name, query_json.dataset_name
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(
        content={
            "initial_epsilon": initial_epsilon,
            "initial_delta": initial_delta,
        }
    )


# MongoDB get total spent budget
@app.post(
    "/get_total_spent_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_total_spent_budget(
    query_json: GetDbData = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    ```
    Returns the spent budget for a user and dataset.

    Args:
        query_json (GetDbData, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to Body(example_get_admin_db_data).

        user_name (str, optional): The user name.
            Defaults to Header(None).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: The user does not exist or
            the user does not have access to the dataset.
    Returns:
        JSONResponse: a JSON object with:
            - total_spent_epsilon (float): total spent epsilon budget.
            - total_spent_delta (float): total spent delta budget.
    ```
    """
    try:
        (
            total_spent_epsilon,
            total_spent_delta,
        ) = ADMIN_DATABASE.get_total_spent_budget(
            user_name, query_json.dataset_name
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(
        content={
            "total_spent_epsilon": total_spent_epsilon,
            "total_spent_delta": total_spent_delta,
        }
    )


# MongoDB get remaining budget
@app.post(
    "/get_remaining_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_remaining_budget(
    query_json: GetDbData = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
        ```
    Returns the remaining budget for a user and dataset.

    Args:
        query_json (GetDbData, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to Body(example_get_admin_db_data).

        user_name (str, optional): The user name.
            Defaults to Header(None).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: The user does not exist or
            the user does not have access to the dataset.
    Returns:
        JSONResponse: a JSON object with:
            - remaining_epsilon (float): remaining epsilon budget.
            - remaining_delta (float): remaining delta budget.
    ```
    """
    try:
        rem_epsilon, rem_delta = ADMIN_DATABASE.get_remaining_budget(
            user_name, query_json.dataset_name
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(
        content={
            "remaining_epsilon": rem_epsilon,
            "remaining_delta": rem_delta,
        }
    )


# MongoDB get archives
@app.post(
    "/get_previous_queries",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_user_previous_queries(
    query_json: GetDbData = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    ```
    Returns the query history of a user on a specific dataset.

    Args:
        query_json (GetDbData, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to Body(example_get_admin_db_data).

        user_name (str, optional): The user name.
            Defaults to Header(None).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: The user does not exist or
            the user does not have access to the dataset.

    Returns:
        JSONResponse: A JSON object containing:
            - previous_queries (list[dict]): a list of dictionaries
              containing the previous queries.
    """
    try:
        previous_queries = ADMIN_DATABASE.get_user_previous_queries(
            user_name, query_json.dataset_name
        )
    except CUSTOM_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content={"previous_queries": previous_queries})
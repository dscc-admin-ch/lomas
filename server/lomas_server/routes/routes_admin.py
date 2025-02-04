from uuid import UUID
from typing import Annotated

from fastapi import APIRouter, Body, Request, Response, Security
from fastapi.responses import JSONResponse, RedirectResponse

from lomas_core.constants import Scopes
from lomas_core.error_handler import (
    KNOWN_EXCEPTIONS,
    InternalServerException,
    UnauthorizedAccessException,
)
from lomas_core.models.collections import Metadata, UserId
from lomas_core.models.config import Config
from lomas_core.models.requests import GetDummyDataset, LomasRequestModel
from lomas_core.models.requests_examples import (
    example_get_admin_db_data,
    example_get_dummy_dataset,
)
from lomas_core.models.responses import (
    ConfigResponse,
    DummyDsResponse,
    InitialBudgetResponse,
    RemainingBudgetResponse,
    SpentBudgetResponse,
)
from lomas_server.data_connector.data_connector import get_column_dtypes
from lomas_server.dp_queries.dummy_dataset import make_dummy_dataset
from lomas_server.routes.utils import get_user_id_from_authenticator
from lomas_server.utils.config import get_config

router = APIRouter()


@router.get("/")
async def root():
    """Redirect root endpoint to the state endpoint.

    Returns:
        JSONResponse: The state of the server instance.
    """
    return RedirectResponse(url="/state")


@router.get("/live")
async def health_handler():
    """HealthCheck endpoint: server alive.

    Returns:
        JSONResponse: "live"
    """
    return JSONResponse(content={"status": "alive"})


@router.get("/status/{uid}")
async def status_handler(request: Request, uid: UUID, response: Response):
    """Job Status endpoint.

    Returns:
        Job
    """
    jobs = request.app.state.jobs_var.get()
    if (job := jobs.get(str(uid))) is not None:
        if job.status == "failed":
            response.status_code = job.status_code
        return job


# Get server state
@router.get("/state", tags=["ADMIN_USER"])
async def get_state(
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
) -> JSONResponse:
    """Returns the current state dict of this server instance.

    Args:
        request (Request): Raw request object
        user_id (UserId): A UserId object identifying the user.

    Returns:
        JSONResponse: The state of the server instance.
    """

    return JSONResponse(
        content={
            "state": "live",
        }
    )

# Get server config
@router.get("/config",
            tags=["ADMIN_USER"],
            response_model=ConfigResponse,
)
async def get_server_config(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
) -> ConfigResponse:
    """Returns the config of this server instance.

    Args:
        request (Request): Raw request object
        user_id (UserId): A UserId object identifying the user.

    Returns:
        ConfigResponse: The server config.
    """
    config = get_config()

    return ConfigResponse(config=config)


# Metadata query
@router.post(
    "/get_dataset_metadata",
    tags=["USER_METADATA"],
)
def get_dataset_metadata(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
) -> Metadata:
    """
    Retrieves metadata for a given dataset.

    Args:
        request (Request): Raw request object
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing
            the dataset_name key for indicating the dataset.
            Defaults to Body(example_get_admin_db_data).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.

    Returns:
        Metadata: The metadata object for the specified
            dataset_name.
    """
    app = request.app

    dataset_name = query_json.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(user_id.name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_id.name} does not have access to {dataset_name}.",
        )

    try:
        ds_metadata = app.state.admin_database.get_dataset_metadata(dataset_name)

    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return ds_metadata


# Dummy dataset query
@router.post(
    "/get_dummy_dataset",
    tags=["USER_DUMMY"],
)
def get_dummy_dataset(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: GetDummyDataset = Body(example_get_dummy_dataset),
) -> DummyDsResponse:
    """
    Generates and returns a dummy dataset.

    Args:
        request (Request): Raw request object
        user_id (UserId): A UserId object identifying the user.
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
        JSONResponse: a dict with the dataframe as a dict, the column types
            and the list of datetime columns.
    """
    app = request.app

    dataset_name = query_json.dataset_name
    if not app.state.admin_database.has_user_access_to_dataset(user_id.name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_id.name} does not have access to {dataset_name}.",
        )

    try:
        ds_metadata = app.state.admin_database.get_dataset_metadata(query_json.dataset_name)
        dtypes, datetime_columns = get_column_dtypes(ds_metadata)

        dummy_df = make_dummy_dataset(
            ds_metadata,
            query_json.dummy_nb_rows,
            query_json.dummy_seed,
        )

        for col in datetime_columns:
            dummy_df[col] = dummy_df[col].dt.strftime("%Y-%m-%dT%H:%M:%S")

    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return DummyDsResponse(dtypes=dtypes, datetime_columns=datetime_columns, dummy_df=dummy_df)


# MongoDB get initial budget
@router.post(
    "/get_initial_budget",
    tags=["USER_BUDGET"],
)
def get_initial_budget(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
) -> InitialBudgetResponse:
    """
    Returns the initial budget for a user and dataset.

    Args:
        request (Request): Raw request object.
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to Body(example_get_admin_db_data).

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
    """
    app = request.app

    try:
        (
            initial_epsilon,
            initial_delta,
        ) = app.state.admin_database.get_initial_budget(user_id.name, query_json.dataset_name)
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return InitialBudgetResponse(initial_epsilon=initial_epsilon, initial_delta=initial_delta)


# MongoDB get total spent budget
@router.post(
    "/get_total_spent_budget",
    tags=["USER_BUDGET"],
)
def get_total_spent_budget(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
) -> SpentBudgetResponse:
    """
    Returns the spent budget for a user and dataset.

    Args:
        request (Request): Raw request object.
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to Body(example_get_admin_db_data).

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
    """
    app = request.app

    try:
        (
            total_spent_epsilon,
            total_spent_delta,
        ) = app.state.admin_database.get_total_spent_budget(user_id.name, query_json.dataset_name)
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return SpentBudgetResponse(total_spent_epsilon=total_spent_epsilon, total_spent_delta=total_spent_delta)


# MongoDB get remaining budget
@router.post(
    "/get_remaining_budget",
    tags=["USER_BUDGET"],
)
def get_remaining_budget(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
) -> RemainingBudgetResponse:
    """
    Returns the remaining budget for a user and dataset.

    Args:
        request (Request): Raw request object.
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to Body(example_get_admin_db_data).

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
    """
    app = request.app

    try:
        rem_epsilon, rem_delta = app.state.admin_database.get_remaining_budget(
            user_id.name, query_json.dataset_name
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return RemainingBudgetResponse(remaining_epsilon=rem_epsilon, remaining_delta=rem_delta)


# MongoDB get archives
@router.post(
    "/get_previous_queries",
    tags=["USER_BUDGET"],
)
def get_user_previous_queries(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
) -> JSONResponse:
    """
    Returns the query history of a user on a specific dataset.

    Args:
        request (Request): Raw request object.
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to Body(example_get_admin_db_data).

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
    app = request.app

    try:
        previous_queries = app.state.admin_database.get_user_previous_queries(
            user_id.name, query_json.dataset_name
        )  # TODO 359 improve on that and return models.
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return JSONResponse(content={"previous_queries": previous_queries})

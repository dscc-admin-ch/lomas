from typing import Annotated
from uuid import UUID

from csvw_eo.datatypes import to_pandas_dtype
from csvw_eo.make_dummy_from_metadata import make_dummy_from_metadata
from csvw_eo.metadata_structure import TableMetadata
from fastapi import APIRouter, Body, Request, Response, Security
from fastapi.responses import JSONResponse, RedirectResponse

from lomas_core.exceptions import (
    JobNotFoundException,
    UnauthorizedAccessException,
)
from lomas_core.models.collections import UserId
from lomas_core.models.constants import JobStatus
from lomas_core.models.requests import GetDummyDataset, LomasRequestModel
from lomas_core.models.requests_examples import (
    EXAMPLE_GET_ADMIN_DB_DATA,
    EXAMPLE_GET_DUMMY_DATASET,
)
from lomas_core.models.responses import (
    Budget,
    DummyDsResponse,
    Job,
)
from lomas_server.auth.auth import ensure_dataset_access
from lomas_server.routes.error_handler import API_ERROR_RESPONSES
from lomas_server.routes.utils import get_user_id_from_authenticator

router = APIRouter()
example_get_admin_db_data_body = Body(EXAMPLE_GET_ADMIN_DB_DATA)
example_get_dummy_dataset_body = Body(EXAMPLE_GET_DUMMY_DATASET)


@router.get("/")
async def root() -> RedirectResponse:
    """Redirect root endpoint to the state endpoint.

    Returns:
        JSONResponse: The state of the server instance.
    """
    return RedirectResponse(url="/state")


@router.get("/live")
async def health_handler() -> JSONResponse:
    """HealthCheck endpoint: server alive.

    Returns:
        JSONResponse: "live"
    """
    return JSONResponse(content={"status": "alive"})


@router.get("/status/{uid}", responses=API_ERROR_RESPONSES)
async def status_handler(
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    request: Request,
    uid: UUID,
    response: Response,
) -> Job:
    """Job status endpoint.

    Args:
        user_id (UserId): The user id.
        request (Request): The raw request.
        uid (UUID): The job's unique id.
        response (Response): The job status response.

    Raises:
        UnauthorizedAccessException: If the user does not have access to this job.
        HTTPException: If the job does not exist.

    Returns:
        Job: The Job model for this uid.
    """
    admin_database = request.app.state.admin_database
    # Check existence
    if not admin_database.does_job_exist(uid):
        raise JobNotFoundException(uid)

    job = admin_database.get_job(uid)

    # Check access rights
    if job.requested_by != user_id.name:
        raise UnauthorizedAccessException(f"User {user_id.name} does not have access to job with uid {uid}")

    if job.status == JobStatus.FAILED:
        response.status_code = job.status_code

    return job


# Metadata query
@router.post(
    "/get_dataset_metadata",
    responses=API_ERROR_RESPONSES,
    tags=["USER_METADATA"],
)
def get_dataset_metadata(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = example_get_admin_db_data_body,
) -> TableMetadata:
    """
    Retrieves metadata for a given dataset.

    Args:
        request (Request): Raw request object
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing
            the dataset_name key for indicating the dataset.
            Defaults to example_get_admin_db_data_body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.

    Returns:
        TableMetadata: The metadata object for the specified dataset_name.
    """
    app = request.app
    dataset_name = query_json.dataset_name

    ensure_dataset_access(user_id, dataset_name, app.state.admin_database)

    ds_metadata = app.state.admin_database.get_dataset_metadata(dataset_name)

    return ds_metadata


# Dummy dataset query
@router.post(
    "/get_dummy_dataset",
    responses=API_ERROR_RESPONSES,
    tags=["USER_DUMMY"],
)
def get_dummy_dataset(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: GetDummyDataset = example_get_dummy_dataset_body,
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

            Defaults to example_get_dummy_dataset_body.

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
    ensure_dataset_access(user_id, dataset_name, app.state.admin_database)

    ds_metadata = app.state.admin_database.get_dataset_metadata(dataset_name)
    dtypes = {col.name: to_pandas_dtype(col.datatype) for col in ds_metadata.columns}
    dummy_df = make_dummy_from_metadata(
        ds_metadata.to_dict(),
        query_json.dummy_nb_rows,
        query_json.dummy_seed,
    )

    return DummyDsResponse(dtypes=dtypes, dummy_df=dummy_df)


@router.post(
    "/get_initial_budget",
    responses=API_ERROR_RESPONSES,
    tags=["USER_BUDGET"],
)
def get_initial_budget(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = example_get_admin_db_data_body,
) -> Budget:
    """
    Returns the initial budget for a user and dataset.

    Args:
        request (Request): Raw request object.
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to example_get_admin_db_data_body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: The user does not exist or
            the user does not have access to the dataset.
    Returns:
        JSONResponse: a JSON object with:
            - epsilon (float): initial epsilon budget.
            - delta (float): initial delta budget.
    """
    app = request.app
    admin_database = app.state.admin_database

    ensure_dataset_access(user_id, query_json.dataset_name, admin_database)
    return admin_database.get_initial_budget(user_id.name, query_json.dataset_name)


@router.post(
    "/get_total_spent_budget",
    responses=API_ERROR_RESPONSES,
    tags=["USER_BUDGET"],
)
def get_total_spent_budget(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = example_get_admin_db_data_body,
) -> Budget:
    """
    Returns the spent budget for a user and dataset.

    Args:
        request (Request): Raw request object.
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to example_get_admin_db_data_body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: The user does not exist or
            the user does not have access to the dataset.
    Returns:
        JSONResponse: a JSON object with:
            - epsilon (float): total spent epsilon budget.
            - delta (float): total spent delta budget.
    """
    app = request.app
    admin_database = app.state.admin_database

    ensure_dataset_access(user_id, query_json.dataset_name, admin_database)

    return admin_database.get_total_spent_budget(user_id.name, query_json.dataset_name)


@router.post(
    "/get_remaining_budget",
    responses=API_ERROR_RESPONSES,
    tags=["USER_BUDGET"],
)
def get_remaining_budget(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = example_get_admin_db_data_body,
) -> Budget:
    """
    Returns the remaining budget for a user and dataset.

    Args:
        request (Request): Raw request object.
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to example_get_admin_db_data_body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: The user does not exist or
            the user does not have access to the dataset.
    Returns:
        JSONResponse: a JSON object with:
            - epsilon (float): remaining epsilon budget.
            - delta (float): remaining delta budget.
    """
    app = request.app
    admin_database = app.state.admin_database

    ensure_dataset_access(user_id, query_json.dataset_name, admin_database)

    return admin_database.get_remaining_budget(user_id.name, query_json.dataset_name)


@router.post(
    "/get_previous_queries",
    responses=API_ERROR_RESPONSES,
    tags=["USER_BUDGET"],
)
def get_user_dataset_queries(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = example_get_admin_db_data_body,
) -> list[Job]:
    """
    Returns the query history of a user on a specific dataset.

    Args:
        request (Request): Raw request object.
        user_id (UserId): A UserId object identifying the user.
        query_json (LomasRequestModel, optional): A JSON object containing:
            - dataset_name (str): The name of the dataset.

            Defaults to example_get_admin_db_data_body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: The user does not exist or
            the user does not have access to the dataset.

    Returns:
        The list of previous jobs for this dataset..
    """
    app = request.app

    ensure_dataset_access(user_id, query_json.dataset_name, app.state.admin_database)

    previous_queries = app.state.admin_database.get_user_dataset_queries(
        user_id.name, query_json.dataset_name
    )

    return previous_queries

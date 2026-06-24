from typing import Annotated
from uuid import UUID

from csvw_eo.datatypes import to_pandas_dtype
from csvw_eo.make_dummy_from_metadata import make_dummy_from_metadata
from csvw_eo.metadata_structure import TableMetadata
from fastapi import APIRouter, Body, Request, Response, Security, UploadFile, status
from fastapi.responses import JSONResponse, RedirectResponse

from lomas_core.constants import Scopes
from lomas_core.exceptions import (
    DatasetNotFoundException,
    JobNotFoundException,
    UnauthorizedAccessException,
    UserNotFoundException,
)
from lomas_core.models.collections import DSInfo, User, UserId
from lomas_core.models.requests import AddDatasetModel, GetDummyDataset, LomasBudgetRequest, LomasRequestModel
from lomas_core.models.requests_examples import (
    example_get_admin_db_data,
    example_get_dummy_dataset,
)
from lomas_core.models.responses import (
    DummyDsResponse,
    InitialBudgetResponse,
    Job,
    RemainingBudgetResponse,
    SpentBudgetResponse,
)
from lomas_server.admin_database.constants import BudgetDBKey
from lomas_server.admin_database.local_database import LocalAdminDatabase
from lomas_server.auth.auth import check_dataset_access
from lomas_server.models.config import Config
from lomas_server.models.responses import ConfigResponse
from lomas_server.routes.error_handler import API_ERROR_RESPONSES
from lomas_server.routes.utils import get_user_id_from_authenticator

router = APIRouter()
example_get_admin_db_data_body = Body(example_get_admin_db_data)
example_get_dummy_dataset_body = Body(example_get_dummy_dataset)


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
    if job.user != user_id.name:
        raise UnauthorizedAccessException(f"User {user_id.name} does not have access to job with uid {uid}")

    if job.status == "failed":
        response.status_code = job.status_code

    # TODO: keep jobs as new archive collection?
    # if job.status == "complete":
    #     # Delete completed job from state once returned to user.
    #     del jobs[str(uid)]

    return job


# Get server state
@router.get("/state", tags=["ADMIN_USER"])
async def get_state(
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
) -> JSONResponse:
    """Returns the current state dict of this server instance.

    Args:
        _ (UserId): A UserId object identifying the user.

    Returns:
        JSONResponse: The state of the server instance.
    """
    return JSONResponse(
        content={
            "state": "live",
        }
    )


# Get server config
@router.get(
    "/config",
    tags=["ADMIN_USER"],
)
async def get_server_config(
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
) -> ConfigResponse:
    """Returns the config of this server instance.

    Args:
        _ (UserId): A UserId object identifying the user.

    Returns:
        ConfigResponse: The server config.
    """
    return ConfigResponse()


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

    check_dataset_access(user_id, dataset_name, app.state.admin_database)

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
    check_dataset_access(user_id, dataset_name, app.state.admin_database)

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
) -> InitialBudgetResponse:
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
            - initial_epsilon (float): initial epsilon budget.
            - initial_delta (float): initial delta budget.
    """
    app = request.app

    (
        initial_epsilon,
        initial_delta,
    ) = app.state.admin_database.get_initial_budget(user_id.name, query_json.dataset_name)

    return InitialBudgetResponse(initial_epsilon=initial_epsilon, initial_delta=initial_delta)


@router.post(
    "/get_total_spent_budget",
    responses=API_ERROR_RESPONSES,
    tags=["USER_BUDGET"],
)
def get_total_spent_budget(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = example_get_admin_db_data_body,
) -> SpentBudgetResponse:
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
            - total_spent_epsilon (float): total spent epsilon budget.
            - total_spent_delta (float): total spent delta budget.
    """
    app = request.app

    (
        total_spent_epsilon,
        total_spent_delta,
    ) = app.state.admin_database.get_total_spent_budget(user_id.name, query_json.dataset_name)

    return SpentBudgetResponse(total_spent_epsilon=total_spent_epsilon, total_spent_delta=total_spent_delta)


@router.post(
    "/get_remaining_budget",
    responses=API_ERROR_RESPONSES,
    tags=["USER_BUDGET"],
)
def get_remaining_budget(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = example_get_admin_db_data_body,
) -> RemainingBudgetResponse:
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
            - remaining_epsilon (float): remaining epsilon budget.
            - remaining_delta (float): remaining delta budget.
    """
    app = request.app

    rem_epsilon, rem_delta = app.state.admin_database.get_remaining_budget(
        user_id.name, query_json.dataset_name
    )

    return RemainingBudgetResponse(remaining_epsilon=rem_epsilon, remaining_delta=rem_delta)


@router.post(
    "/get_previous_queries",
    responses=API_ERROR_RESPONSES,
    tags=["USER_BUDGET"],
)
def get_user_previous_queries(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_authenticator)],
    query_json: LomasRequestModel = example_get_admin_db_data_body,
) -> JSONResponse:
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
        JSONResponse: A JSON object containing:
            - previous_queries (list[dict]): a list of dictionaries
              containing the previous queries.
    """
    app = request.app

    check_dataset_access(user_id, query_json.dataset_name, app.state.admin_database)

    previous_queries = app.state.admin_database.get_user_previous_queries(
        user_id.name, query_json.dataset_name
    )  # TODO 359 improve on that and return models.

    return JSONResponse(content={"previous_queries": previous_queries})


#############################
# ADMIN DASHBOARD MIGRATION #
#############################


@router.get("/datasets", responses=API_ERROR_RESPONSES)
def list_datasets(
    request: Request, _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])]
) -> list[str]:
    db: LocalAdminDatabase = request.app.state.admin_database
    return [ds.dataset_name for ds in db.datasets()]


@router.get("/users", responses=API_ERROR_RESPONSES)
def list_users(
    request: Request, _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])]
) -> list[User]:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.users()


@router.post("/users", responses=API_ERROR_RESPONSES)
def add_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    new_user: User,
) -> None:
    """Adds a new user with an associated budget for a given dataset.

    Args:
        new_user (User): User to add
    """
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.add_user(new_user.id.name, new_user.id.email)


@router.post("/usersfile", responses=API_ERROR_RESPONSES)
def add_users_yaml(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    file: UploadFile,
    clean: bool = False,
) -> None:
    """Add all users from a yaml file.

    Args:
        file (Path): a path to the YAML file location
        clean (bool): boolean flag
            True if drop current user collection
            False if keep current user collection
    """
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.add_users_via_yaml(file.file, clean=clean)


@router.delete("/users/{username}", responses=API_ERROR_RESPONSES)
def delete_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
) -> None:
    """Deletes the lomas user.

    Args:
        username (str): The name of the user to be deleted.
    """
    db: LocalAdminDatabase = request.app.state.admin_database

    if not db.does_user_exist(username):
        raise UserNotFoundException(username)

    return db.del_user(username)


@router.delete("/collections/{collection_name}", responses=API_ERROR_RESPONSES)
def delete_collection(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    collection_name: str,
) -> None:
    """Drops the given collection from the administration database.

    Args:
        collection_name (str): The collection to drop.
    """
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.drop_collection(collection_name)


@router.post("/dataset/bulk", responses=API_ERROR_RESPONSES)
def add_dataset_bulk(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    file: UploadFile,
    clean: bool = False,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    config = Config()
    return db.add_datasets_via_yaml(file.file, clean=clean, path_prefix=config.data_directory)


@router.post("/dataset", responses=API_ERROR_RESPONSES)
def add_dataset(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    body: AddDatasetModel,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.add_dataset(
        body.dataset_name,
        body.database_type,
        body.metadata_database_type,
        body.dataset_path,
        body.metadata_path,
    )


@router.delete("/dataset/{dataset_name}", responses=API_ERROR_RESPONSES)
def delete_dataset(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.del_dataset(dataset_name)


@router.patch("/users/{username}/dataset", responses=API_ERROR_RESPONSES)
def add_dataset_to_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
    body: LomasRequestModel,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.add_dataset_to_user(username, body.dataset_name, 0.0, 0.0)


@router.patch("/users/{username}/dataset/del", responses=API_ERROR_RESPONSES)
def del_dataset_to_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
    body: LomasRequestModel,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.del_dataset_to_user(username, body.dataset_name)


@router.patch("/users/{username}/dataset/budget", responses=API_ERROR_RESPONSES)
def set_epsilon_delta(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
    body: LomasBudgetRequest,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    db.set_epsilon_or_delta(username, body.dataset_name, BudgetDBKey.EPSILON_INIT, body.epsilon)
    db.set_epsilon_or_delta(username, body.dataset_name, BudgetDBKey.DELTA_INIT, body.delta)


@router.get("/users/{username}/archive", responses=API_ERROR_RESPONSES)
def get_archives_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
) -> list[dict]:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.get_archives_of_user(username)


@router.get("/dataset/{dataset_name}", responses=API_ERROR_RESPONSES)
def get_dataset(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
) -> DSInfo:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.get_dataset(dataset_name)


@router.get("/dataset/{dataset_name}/metadata", responses=API_ERROR_RESPONSES)
def get_dataset_metadata_admin(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
) -> TableMetadata:
    db: LocalAdminDatabase = request.app.state.admin_database

    if not db.does_dataset_exist(dataset_name):
        raise DatasetNotFoundException(dataset_name)

    return db.get_dataset_metadata(dataset_name)


@router.patch("/dataset/{dataset_name}/metadata", responses=API_ERROR_RESPONSES)
def set_dataset_metadata_admin(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
    file: UploadFile,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database

    if not db.does_dataset_exist(dataset_name):
        raise DatasetNotFoundException(dataset_name)

    db.set_dataset_metadata(dataset_name, file.file)


@router.get("/bootstrap", responses=API_ERROR_RESPONSES)
def get_bootstrap(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    response: Response,
) -> None:
    # Just returns ok if bootstrap still set.
    if request.app.state.admin_database.get_bootstrap_disabled():
        response.status_code = status.HTTP_410_GONE
    else:
        response.status_code = status.HTTP_200_OK


@router.delete("/bootstrap", responses=API_ERROR_RESPONSES)
def delete_bootstrap(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    response: Response,
) -> None:
    # Bootstrap never set or already removed -> gone forever
    if request.app.state.admin_database.get_bootstrap_disabled():
        response.status_code = status.HTTP_410_GONE
    else:
        request.app.state.admin_database.set_bootstrap_disabled(True)

from typing import Annotated
from uuid import UUID

from csvw_safe.make_dummy_from_metadata import make_dummy_from_metadata
from csvw_safe.metadata_structure import TableMetadata
from fastapi import APIRouter, Body, HTTPException, Request, Response, Security, UploadFile, status
from fastapi.responses import JSONResponse, RedirectResponse

from lomas_core.constants import Scopes
from lomas_core.error_handler import (
    KNOWN_EXCEPTIONS,
    SERVER_QUERY_ERROR_RESPONSES,
    InternalServerException,
    UnauthorizedAccessException,
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
from lomas_server.data_connector.data_connector import get_column_dtypes
from lomas_server.models.config import Config
from lomas_server.models.responses import ConfigResponse
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


@router.get("/status/{uid}", responses=SERVER_QUERY_ERROR_RESPONSES)
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
    jobs = request.app.state.jobs
    if (job := jobs.get(str(uid))) is not None:
        if job.requested_by != user_id.name:
            raise UnauthorizedAccessException(f"{user_id.name} does not have access to job with uid {uid}.")

        if job.status == "failed":
            response.status_code = job.status_code

        if job.status == "complete":
            # Delete completed job from state once returned to user.
            del jobs[str(uid)]

        return job
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This job does not exist.")


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
    if not app.state.admin_database.has_user_access_to_dataset(user_id.name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_id.name} does not have access to {dataset_name}.",
        )

    try:
        ds_metadata = app.state.admin_database.get_dataset_metadata(query_json.dataset_name)
        dtypes = get_column_dtypes(ds_metadata)

        dummy_df = make_dummy_from_metadata(
            ds_metadata,
            query_json.dummy_nb_rows,
            query_json.dummy_seed,
        )

    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return DummyDsResponse(dtypes=dtypes, dummy_df=dummy_df)


@router.post(
    "/get_initial_budget",
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


@router.post(
    "/get_total_spent_budget",
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


@router.post(
    "/get_remaining_budget",
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

    try:
        rem_epsilon, rem_delta = app.state.admin_database.get_remaining_budget(
            user_id.name, query_json.dataset_name
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return RemainingBudgetResponse(remaining_epsilon=rem_epsilon, remaining_delta=rem_delta)


@router.post(
    "/get_previous_queries",
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

    try:
        previous_queries = app.state.admin_database.get_user_previous_queries(
            user_id.name, query_json.dataset_name
        )  # TODO 359 improve on that and return models.
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e
    return JSONResponse(content={"previous_queries": previous_queries})


#############################
# ADMIN DASHBOARD MIGRATION #
#############################


@router.get("/datasets")
def list_datasets(
    request: Request, _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])]
) -> list[str]:
    db: LocalAdminDatabase = request.app.state.admin_database
    return [ds.dataset_name for ds in db.datasets()]


@router.get("/users")
def list_users(
    request: Request, _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])]
) -> list[User]:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.users()


@router.post("/users")
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


@router.post("/usersfile")
def add_users_yaml(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    file: UploadFile,
    clean: bool = False,
) -> None:
    """Add all users from a yaml file.

    Args:
        yaml_file (Path): a path to the YAML file location
        clean (bool): boolean flag
            True if drop current user collection
            False if keep current user collection
    """
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.add_users_via_yaml(file.file, clean=clean)


@router.delete("/users/{username}")
def delete_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
) -> None:
    """Deletes the lomas user.

    Args:
        user_name (str): The name of the user to be deleted.
    """
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.del_user(username)


@router.delete("/collections/{collection_name}")
def delete_collection(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    collection_name: str,
) -> None:
    """Drops the given collection from the administration database.

    Args:
        collection (str): The collection to drop.
    """
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.drop_collection(collection_name)


@router.post("/dataset/bulk")
def add_dataset_bulk(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    file: UploadFile,
    clean: bool = False,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    config = Config()
    return db.add_datasets_via_yaml(file.file, clean=clean, path_prefix=config.data_directory)


@router.post("/dataset")
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


@router.delete("/dataset/{dataset_name}")
def delete_dataset(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.del_dataset(dataset_name)


@router.patch("/users/{username}/dataset")
def add_dataset_to_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
    body: LomasRequestModel,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.add_dataset_to_user(username, body.dataset_name, 0.0, 0.0)


@router.patch("/users/{username}/dataset/del")
def del_dataset_to_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
    body: LomasRequestModel,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.del_dataset_to_user(username, body.dataset_name)


@router.patch("/users/{username}/dataset/budget")
def set_epsilon_delta(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
    body: LomasBudgetRequest,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    db.set_epsilon_or_delta(username, body.dataset_name, BudgetDBKey.EPSILON_INIT, body.epsilon)
    db.set_epsilon_or_delta(username, body.dataset_name, BudgetDBKey.DELTA_INIT, body.delta)


@router.get("/users/{username}/archive")
def get_archives_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
) -> list[dict]:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.get_archives_of_user(username)


@router.get("/dataset/{dataset_name}")
def get_dataset(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
) -> DSInfo:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.get_dataset(dataset_name)


@router.get("/dataset/{dataset_name}/metadata")
def get_dataset_metadata_admin(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
) -> TableMetadata:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.get_dataset_metadata(dataset_name)


@router.patch("/dataset/{dataset_name}/metadata")
def set_dataset_metadata_admin(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
    file: UploadFile,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    db.set_dataset_metadata(dataset_name, file.file)


@router.delete("/bootstrap")
def delete_bootstrap(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    response: Response,
) -> None:
    # Bootstrap never set or already removed -> gone forever
    if request.app.state.bootstrap is None:
        response.status_code = status.HTTP_410_GONE
    else:
        request.app.state.bootstrap = None

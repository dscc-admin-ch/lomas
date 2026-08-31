from typing import Annotated

import httpx
from csvw_eo.metadata_structure import TableMetadata
from fastapi import APIRouter, Body, Form, Request, Response, Security, UploadFile, status
from fastapi.responses import JSONResponse, RedirectResponse

from lomas_core.constants import Scopes
from lomas_core.exceptions import (
    DatasetNotFoundException,
    InvalidQueryException,
    UserNotFoundException,
)
from lomas_core.models.collections import DSInfo, User, UserId
from lomas_core.models.requests import AddDatasetModel, LomasBudgetRequest, LomasRequestModel
from lomas_core.models.requests_examples import (
    EXAMPLE_GET_ADMIN_DB_DATA,
    EXAMPLE_GET_DUMMY_DATASET,
)
from lomas_core.models.responses import (
    Budget,
    Job,
)
from lomas_server.admin_database.constants import BudgetDBKey
from lomas_server.admin_database.local_database import LocalAdminDatabase
from lomas_server.models.responses import ConfigResponse
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
async def health_handler(request: Request) -> JSONResponse:
    """HealthCheck endpoint: server alive.

    Returns:
        JSONResponse: "live"
    """
    config = request.app.state.config
    port = config.user_host_port
    url = f"http://localhost:{port}/live"

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url)  # without await -> deadlock
            if response.status_code == status.HTTP_200_OK and response.json().get("status") == "alive":
                return JSONResponse(content={"status": "alive"})

    except (httpx.RequestError, Exception):
        pass

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unhealthy", "detail": "User server is not alive"},
    )


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


#############################
# ADMIN DASHBOARD           #
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
def put_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    new_user: User,
) -> None:
    """Adds a new user with an associated budget for a given dataset.

    Args:
        new_user (User): User to add
    """
    db: LocalAdminDatabase = request.app.state.admin_database
    try:
        return db.put_user(new_user)
    except KeyError as e:
        raise InvalidQueryException(str(e)) from e


@router.post("/usersfile", responses=API_ERROR_RESPONSES)
def add_users_yaml(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    file: UploadFile,
    clean: Annotated[bool, Form()],
    overwrite: Annotated[bool, Form()],
    # data: Annotated[FormData, Form()] | None = None
) -> None:
    """Add all users from a yaml file.

    Args:
        file (Path): a path to the YAML file location
        clean (bool): boolean flag
            True if drop current user collection
            False if keep current user collection
    """
    db: LocalAdminDatabase = request.app.state.admin_database
    try:
        return db.add_users_via_yaml(file.file, clean=clean, overwrite=overwrite)
    except KeyError as e:
        raise InvalidQueryException(str(e)) from e


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
    clean: Annotated[bool, Form()],
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database
    config = request.app.state.config
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

    if not db.does_user_exist(username):
        raise UserNotFoundException(username)

    return db.add_dataset_to_user(username, body.dataset_name, Budget.zero())


@router.patch("/users/{username}/dataset/del", responses=API_ERROR_RESPONSES)
def del_dataset_to_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
    body: LomasRequestModel,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database

    if not db.does_user_exist(username):
        raise UserNotFoundException(username)

    return db.del_dataset_to_user(username, body.dataset_name)


@router.patch("/users/{username}/dataset/budget", responses=API_ERROR_RESPONSES)
def set_epsilon_delta(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
    body: LomasBudgetRequest,
) -> None:
    db: LocalAdminDatabase = request.app.state.admin_database

    if not db.does_user_exist(username):
        raise UserNotFoundException(username)

    db.set_epsilon_or_delta(
        username, body.dataset_name, BudgetDBKey.INITIAL, Budget(epsilon=body.epsilon, delta=body.delta)
    )


@router.get("/users/{username}/archive", responses=API_ERROR_RESPONSES)
def get_archives_user(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    username: str,
) -> list[Job]:
    db: LocalAdminDatabase = request.app.state.admin_database

    if not db.does_user_exist(username):
        raise UserNotFoundException(username)

    return db.get_user_queries(username)


@router.get("/dataset/{dataset_name}", responses=API_ERROR_RESPONSES)
def get_dataset(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_authenticator, scopes=[Scopes.ADMIN])],
    dataset_name: str,
) -> DSInfo:
    db: LocalAdminDatabase = request.app.state.admin_database

    if not db.does_dataset_exist(dataset_name):
        raise DatasetNotFoundException(dataset_name)

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

import random
import time
from functools import wraps
from pathlib import Path
from typing import Annotated

from aio_pika.patterns.rpc import Proxy
from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer, SecurityScopes

from lomas_core.constants import DPLibraries
from lomas_core.exceptions import (
    InternalServerException,
)
from lomas_core.models.collections import DSPathAccess, DSS3Access, UserId
from lomas_core.models.constants import (
    LomasHeaders,
    PrivateDatabaseType,
    TimeAttackMethod,
    get_lomas_logger,
)
from lomas_core.models.requests import (
    DummyQueryModel,
    LomasRequestModel,
    QueryModel,
)
from lomas_core.models.responses import Job
from lomas_server.auth.auth import authorize_user, ensure_dataset_access
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.data_connector.path_connector import PathConnector
from lomas_server.data_connector.s3_connector import S3Connector
from lomas_server.models.config import PrivateDBCredentials, S3CredentialsConfig, ServerConfig

logger = get_lomas_logger(__name__)


def timing_protection(func):  # type: ignore[no-untyped-def]
    """Adds delays to requests response to protect against timing attack."""

    @wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore[no-untyped-def]
        config = ServerConfig()

        start_time = time.time()
        response = func(*args, **kwargs)
        process_time = time.time() - start_time

        match config.time_attack.method:
            case TimeAttackMethod.STALL:
                # Slows to a minimum response time defined by magnitude
                if process_time < config.time_attack.magnitude:
                    time.sleep(config.time_attack.magnitude - process_time)
            case TimeAttackMethod.JITTER:
                # Adds some time between 0 and magnitude secs
                time.sleep(config.time_attack.magnitude * random.uniform(0, 1))
        return response

    return wrapper


def get_user_id_from_api_key(
    request: Request,
    api_key: Annotated[str, Depends(APIKeyHeader(name=LomasHeaders.APIKEY))],
) -> UserId:
    # TODO: validate api_key
    # Allow worker to impersonate Users Id for db queries
    name = request.headers.get(LomasHeaders.FORUSER, LomasHeaders.WORKERUSER)
    return UserId(name=name, email="api@noreply.com")


def get_user_id_from_authenticator(
    request: Request,
    security_scopes: SecurityScopes,
    auth_creds: Annotated[HTTPAuthorizationCredentials, Depends(HTTPBearer())],
) -> UserId:
    """Extracts the authenticator from the app state and calls its get_user_id method.

    Also adds the user_name to the request state to annotate the telemetry request span.

    Args:
        request (Request): The request to access the app and state.
        security_scopes (SecurityScopes): The required scopes for the endpoint.
        auth_creds (Annotated[HTTPAuthorizationCredentials, Depends): The HTTP bearer token.

    Returns:
        UserId: A UserId instance extracted from the token.
    """
    # Bootstrap initialization
    if not request.app.state.admin_database.get_bootstrap_disabled():
        bootstrap_cred = request.app.state.admin_database.get_bootstrap()
        match auth_creds:
            case HTTPAuthorizationCredentials(scheme="Bearer") if auth_creds.credentials == bootstrap_cred:
                logger.warning("Bootstrap User Bypass")
                user_id = UserId(name="bootstrap", email="boot@strap.com")
                request.state.user_name = user_id.name
                return user_id
            case _:
                pass

    user_id = request.app.state.authenticator.get_user_id(auth_creds.credentials)
    request.state.user_name = user_id.name
    # This raises an exception if authz fails
    authorize_user(user_id, request.app.state.admin_database, security_scopes)

    return user_id


def get_dataset_credentials(
    private_db_credentials: dict[int, PrivateDBCredentials],
    db_type: PrivateDatabaseType,
    credentials_name: str,
) -> PrivateDBCredentials:
    """
    Search the list of private database credentials and.

    returns the one that matches the database type and
    credentials name.

    Args:
        private_db_credentials (Sequence[PrivateDBCredentials]):\
            The list of private database credentials.
        db_type (PrivateDatabaseType): The type of the database.

    Raises:
        InternalServerException: If the credentials are not found.

    Returns:
        PrivateDBCredentials: The matching credentials.
    """
    if db_type == PrivateDatabaseType.S3:
        for c in private_db_credentials.values():
            if isinstance(c, S3CredentialsConfig) and (credentials_name == c.credentials_name):
                return c

    raise InternalServerException(
        "Could not find credentials for private dataset. Please contact server administrator."
    )


@timing_protection
def handle_query_to_job(
    request: Request,
    query: DummyQueryModel | QueryModel | LomasRequestModel,
    user: UserId,
    dp_library: DPLibraries,
) -> Job:
    """
    Submit Job to handles queries on private, dummy and cost datasets on a worker.

    Args:
        request (Request): Raw request object
        query (DummyQueryModel|QueryModel|LomasRequestModel): A Request or Query to be scheduled
        user_name (str): The user name
        dp_library (DPLibraries): Name of the DP library to use for the request

    Raises:
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        Job: A scheduled Job resulting in a QueryResponse containing the result of the query
            (specific to the library) as well as the cost of the query.
            or a CostResponse containing the epsilon, delta and privacy-loss budget cost for the request.
    """
    app = request.app
    admin_database = app.state.admin_database

    dataset_name = query.dataset_name

    ensure_dataset_access(user, dataset_name, admin_database)

    new_task = Job(requested_by=user.name, dataset_name=dataset_name, query=query)

    # app.state.jobs[str(new_task.uid)] = new_task
    admin_database.put_job(new_task)

    return new_task


def get_dataset_connector(
    admin_database: Proxy, dataset_name: str, private_db_credentials: dict[int, PrivateDBCredentials]
) -> DataConnector:
    """Returns the proper dataset connector.

    Args:
        admin_database (AdminDatabase): An AdminDatabase instance to get dataset information from.
        dataset_name (str): The name of the dataset.
        private_db_credentials (dict[int, PrivateDBCredentials]): The dict of all dataset credentials.

    Raises:
        InternalServerException: In case the dataset type does not exist.
    """
    ds_info = admin_database.get_dataset(dataset_name=dataset_name)
    ds_access = ds_info.dataset_access
    ds_metadata = admin_database.get_dataset_metadata(dataset_name=dataset_name)
    data_connector = None

    match ds_access:
        case DSPathAccess():
            match path := ds_access.path:
                case Path():
                    data_connector = PathConnector(metadata=ds_metadata, dataset_path=path.resolve())
                case _:
                    data_connector = PathConnector(metadata=ds_metadata, dataset_path=path)
        case DSS3Access():
            credentials = get_dataset_credentials(
                private_db_credentials,
                ds_access.database_type,
                ds_access.credentials_name,
            )

            if not isinstance(credentials, S3CredentialsConfig):
                raise InternalServerException("Could not get correct credentials")

            ds_access = DSS3Access.model_validate(ds_access)
            ds_access.access_key_id = credentials.access_key_id
            ds_access.secret_access_key = credentials.secret_access_key

            data_connector = S3Connector(metadata=ds_metadata, credentials=ds_access)
        case _:
            raise InternalServerException(f"Unknown database type: {ds_access.database_type}")

    return data_connector

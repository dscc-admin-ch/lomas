from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.responses import JSONResponse, RedirectResponse
from lomas_core.error_handler import (
    KNOWN_EXCEPTIONS,
    InternalServerException,
    UnauthorizedAccessException,
)
from lomas_core.models.collections import Metadata
from lomas_core.models.requests import GetDummyDataset, LomasRequestModel
from lomas_core.models.responses import (
    DummyDsResponse,
    InitialBudgetResponse,
    RemainingBudgetResponse,
    SpentBudgetResponse,
)

from lomas_server.data_connector.data_connector import get_column_dtypes
from lomas_server.dp_queries.dummy_dataset import make_dummy_dataset
from lomas_server.routes.utils import server_live
from lomas_server.utils.query_examples import (
    example_get_admin_db_data,
    example_get_dummy_dataset,
)

router = APIRouter()


@router.get("/")
async def root():
    """Redirect root endpoint to the state endpoint.

    Returns:
        JSONResponse: The state of the server instance.
    """
    return RedirectResponse(url="/state")


# Get server state
@router.get("/state", tags=["ADMIN_USER"])
async def get_state(
    request: Request,
    user_name: str = Header(None),
) -> JSONResponse:
    """Returns the current state dict of this server instance.

    Args:
        request (Request): Raw request object
        user_name (str, optional): The user name. Defaults to Header(None).

    Returns:
        JSONResponse: The state of the server instance.
    """
    app = request.app

    return JSONResponse(
        content={
            "requested_by": user_name,
            "state": app.state.server_state,
        }
    )


# Metadata query
@router.post(
    "/get_dataset_metadata",
    dependencies=[Depends(server_live)],
    tags=["USER_METADATA"],
)
def get_dataset_metadata(
    request: Request,
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> Metadata:
    """
    Retrieves metadata for a given dataset.

    Args:
        request (Request): Raw request object
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
    if not app.state.admin_database.has_user_access_to_dataset(user_name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_name} does not have access to {dataset_name}.",
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
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def get_dummy_dataset(
    request: Request,
    query_json: GetDummyDataset = Body(example_get_dummy_dataset),
    user_name: str = Header(None),
) -> DummyDsResponse:
    """
    Generates and returns a dummy dataset.

    Args:
        request (Request): Raw request object
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
    if not app.state.admin_database.has_user_access_to_dataset(user_name, dataset_name):
        raise UnauthorizedAccessException(
            f"{user_name} does not have access to {dataset_name}.",
        )

    try:
        ds_metadata = app.state.admin_database.get_dataset_metadata(
            query_json.dataset_name
        )
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

    return DummyDsResponse(
        dtypes=dtypes, datetime_columns=datetime_columns, dummy_df=dummy_df
    )


# MongoDB get initial budget
@router.post(
    "/get_initial_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_initial_budget(
    request: Request,
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> InitialBudgetResponse:
    """
    Returns the initial budget for a user and dataset.

    Args:
        request (Request): Raw request object
        query_json (LomasRequestModel, optional): A JSON object containing:
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
    """
    app = request.app

    try:
        (
            initial_epsilon,
            initial_delta,
        ) = app.state.admin_database.get_initial_budget(
            user_name, query_json.dataset_name
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return InitialBudgetResponse(
        initial_epsilon=initial_epsilon, initial_delta=initial_delta
    )


# MongoDB get total spent budget
@router.post(
    "/get_total_spent_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_total_spent_budget(
    request: Request,
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> SpentBudgetResponse:
    """
    Returns the spent budget for a user and dataset.

    Args:
        request (Request): Raw request object
        query_json (LomasRequestModel, optional): A JSON object containing:
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
    """
    app = request.app

    try:
        (
            total_spent_epsilon,
            total_spent_delta,
        ) = app.state.admin_database.get_total_spent_budget(
            user_name, query_json.dataset_name
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return SpentBudgetResponse(
        total_spent_epsilon=total_spent_epsilon, total_spent_delta=total_spent_delta
    )


# MongoDB get remaining budget
@router.post(
    "/get_remaining_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_remaining_budget(
    request: Request,
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> RemainingBudgetResponse:
    """
    Returns the remaining budget for a user and dataset.

    Args:
        request (Request): Raw request object
        query_json (LomasRequestModel, optional): A JSON object containing:
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
    """
    app = request.app

    try:
        rem_epsilon, rem_delta = app.state.admin_database.get_remaining_budget(
            user_name, query_json.dataset_name
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return RemainingBudgetResponse(
        remaining_epsilon=rem_epsilon, remaining_delta=rem_delta
    )


# MongoDB get archives
@router.post(
    "/get_previous_queries",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_user_previous_queries(
    request: Request,
    query_json: LomasRequestModel = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Returns the query history of a user on a specific dataset.

    Args:
        request (Request): Raw request object
        query_json (LomasRequestModel, optional): A JSON object containing:
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
    app = request.app

    try:
        previous_queries = app.state.admin_database.get_user_previous_queries(
            user_name, query_json.dataset_name
        )  # TODO 359 improve on that and return models.
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(str(e)) from e

    return JSONResponse(content={"previous_queries": previous_queries})

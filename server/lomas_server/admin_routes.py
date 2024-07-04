from fastapi import APIRouter, Request, Body, Depends, Header
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse

from app import app
from dp_queries.dummy_dataset import make_dummy_dataset
from utils.error_handler import KNOWN_EXCEPTIONS, InternalServerException
from utils.example_inputs import (
    example_get_admin_db_data,
    example_get_dummy_dataset,
)
from utils.input_models import GetDbData, GetDummyDataset
from utils.utils import server_live, stream_dataframe


router = APIRouter()


@app.get("/")
async def root():
    """Redirect root endpoint to the state endpoint
    Returns:
        JSONResponse: The state of the server instance.
    """
    return RedirectResponse(url="/state")


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
            "state": app.state.server_state,
        }
    )


@app.get(
    "/get_memory_usage",
    dependencies=[Depends(server_live)],
    tags=["ADMIN_USER"],
)
async def get_memory_usage() -> JSONResponse:
    """Return the dataset store object memory usage
    Args:
        user_name (str, optional): The user name. Defaults to Header(None).

    Returns:
        JSONResponse: with DatasetStore object memory usage
    """
    return JSONResponse(
        content={
            "memory_usage": app.state.dataset_store.memory_usage,
        }
    )


# Metadata query
@app.post(
    "/get_dataset_metadata",
    dependencies=[Depends(server_live)],
    tags=["USER_METADATA"],
)
def get_dataset_metadata(
    _request: Request,
    query_json: GetDbData = Body(example_get_admin_db_data),
) -> JSONResponse:
    """
    Retrieves metadata for a given dataset.

    Args:
        request (Request): Raw request object
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
    """
    try:
        ds_metadata = app.state.admin_database.get_dataset_metadata(
            query_json.dataset_name
        )

    except KNOWN_EXCEPTIONS as e:
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
    _request: Request,
    query_json: GetDummyDataset = Body(example_get_dummy_dataset),
) -> StreamingResponse:
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
        StreamingResponse: a pd.DataFrame representing the dummy dataset.
    """
    try:
        ds_metadata = app.state.admin_database.get_dataset_metadata(
            query_json.dataset_name
        )

        dummy_df = make_dummy_dataset(
            ds_metadata, query_json.dummy_nb_rows, query_json.dummy_seed
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return stream_dataframe(dummy_df)


# MongoDB get initial budget
@app.post(
    "/get_initial_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_initial_budget(
    _request: Request,
    query_json: GetDbData = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Returns the initial budget for a user and dataset.

    Args:
        request (Request): Raw request object
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
    """
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
    _request: Request,
    query_json: GetDbData = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Returns the spent budget for a user and dataset.

    Args:
        request (Request): Raw request object
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
    """
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
    _request: Request,
    query_json: GetDbData = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Returns the remaining budget for a user and dataset.

    Args:
        request (Request): Raw request object
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
    """
    try:
        rem_epsilon, rem_delta = app.state.admin_database.get_remaining_budget(
            user_name, query_json.dataset_name
        )
    except KNOWN_EXCEPTIONS as e:
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
    _request: Request,
    query_json: GetDbData = Body(example_get_admin_db_data),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Returns the query history of a user on a specific dataset.

    Args:
        request (Request): Raw request object
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
        previous_queries = app.state.admin_database.get_user_previous_queries(
            user_name, query_json.dataset_name
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content={"previous_queries": previous_queries})

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import SERVER_QUERY_ERROR_RESPONSES
from lomas_core.models.requests import (
    DiffPrivLibDummyQueryModel,
    DiffPrivLibQueryModel,
    DiffPrivLibRequestModel,
    OpenDPDummyQueryModel,
    OpenDPQueryModel,
    OpenDPRequestModel,
    SmartnoiseSQLDummyQueryModel,
    SmartnoiseSQLQueryModel,
    SmartnoiseSQLRequestModel,
    SmartnoiseSynthDummyQueryModel,
    SmartnoiseSynthQueryModel,
    SmartnoiseSynthRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse
from lomas_server.routes.utils import (
    handle_cost_query,
    handle_query_on_dummy_dataset,
    handle_query_on_private_dataset,
    server_live,
)

router = APIRouter()

# Smartnoise SQL
# -----------------------------------------------------------------------------


@router.post(
    "/smartnoise_sql_query",
    dependencies=[Depends(server_live)],
    response_model=QueryResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def smartnoise_sql_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_sql_query: SmartnoiseSQLQueryModel,
) -> QueryResponse:
    """
    Handles queries for the SmartNoiseSQL library.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        smartnoise_sql_query (SmartnoiseSQLQueryModel): The smartnoise_sql query body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        QueryResponse: A query response containing a SmartnoiseSQLQueryResult.
    """
    return handle_query_on_private_dataset(
        request, smartnoise_sql_query, user_name, DPLibraries.SMARTNOISE_SQL
    )


@router.post(
    "/dummy_smartnoise_sql_query",
    dependencies=[Depends(server_live)],
    response_model=QueryResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_DUMMY"],
)
def dummy_smartnoise_sql_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_sql_query: SmartnoiseSQLDummyQueryModel,
) -> QueryResponse:
    """
    Handles queries on dummy datasets for the SmartNoiseSQL library.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        smartnoise_sql_query (SmartnoiseSQLDummyQueryModel):
            The smartnoise_sql query body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        QueryResponse: A query response containing a SmartnoiseSQLQueryResult.
    """
    return handle_query_on_dummy_dataset(request, smartnoise_sql_query, user_name, DPLibraries.SMARTNOISE_SQL)


@router.post(
    "/estimate_smartnoise_sql_cost",
    dependencies=[Depends(server_live)],
    response_model=CostResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def estimate_smartnoise_sql_cost(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_sql_query: SmartnoiseSQLRequestModel,
) -> CostResponse:
    """
    Estimates the privacy loss budget cost of a SmartNoiseSQL query.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        smartnoise_sql_query (SmartnoiseSQLRequestModel):
            The smartnoise_sql request body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        CostResponse: The privacy loss cost of the input query.
    """
    return handle_cost_query(request, smartnoise_sql_query, user_name, DPLibraries.SMARTNOISE_SQL)


# Smartnoise Synth
# -----------------------------------------------------------------------------


@router.post(
    "/smartnoise_synth_query",
    dependencies=[Depends(server_live)],
    response_model=QueryResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def smartnoise_synth_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_synth_query: SmartnoiseSynthQueryModel,
) -> QueryResponse:
    """
    Handles queries for the SmartNoiseSynth library.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        smartnoise_synth_query (SmartnoiseSynthQueryModel):
            The smartnoise_synth query body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        QueryResponse: A query response containing a SmartnoiseSynthModel
        or SmartnoiseSynthSamples.
    """
    return handle_query_on_private_dataset(
        request, smartnoise_synth_query, user_name, DPLibraries.SMARTNOISE_SYNTH
    )


@router.post(
    "/dummy_smartnoise_synth_query",
    dependencies=[Depends(server_live)],
    response_model=QueryResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def dummy_smartnoise_synth_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_synth_query: SmartnoiseSynthDummyQueryModel,
) -> QueryResponse:
    """
    Handles queries on dummy datasets for the SmartNoiseSynth library.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        smartnoise_synth_query (SmartnoiseSynthDummyQueryModel):
            The smartnoise_synth query body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        QueryResponse: A query response containing a SmartnoiseSynthModel
        or SmartnoiseSynthSamples.
    """
    return handle_query_on_dummy_dataset(
        request, smartnoise_synth_query, user_name, DPLibraries.SMARTNOISE_SYNTH
    )


@router.post(
    "/estimate_smartnoise_synth_cost",
    dependencies=[Depends(server_live)],
    response_model=CostResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def estimate_smartnoise_synth_cost(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_synth_query: SmartnoiseSynthRequestModel,
) -> CostResponse:
    """
    Computes the privacy loss budget cost of a SmartNoiseSynth query.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        smartnoise_synth_query (SmartnoiseSynthRequestModel):
            The smartnoise_synth query body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        CostResponse: The privacy loss cost of the input query.
    """
    return handle_cost_query(request, smartnoise_synth_query, user_name, DPLibraries.SMARTNOISE_SYNTH)


# OpenDP
# -----------------------------------------------------------------------------


@router.post(
    "/opendp_query",
    dependencies=[Depends(server_live)],
    response_model=QueryResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def opendp_query_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    opendp_query: OpenDPQueryModel,
) -> QueryResponse:
    """
    Handles queries for the OpenDP Library.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object.
        opendp_query (OpenDPQueryModel): The opendp query object.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The pipeline does not contain a "measurement",
            there is not enough budget or the dataset does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        QueryResponse: A query response containing an OpenDPQueryResult.
    """
    return handle_query_on_private_dataset(request, opendp_query, user_name, DPLibraries.OPENDP)


@router.post(
    "/dummy_opendp_query",
    dependencies=[Depends(server_live)],
    response_model=QueryResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_DUMMY"],
)
def dummy_opendp_query_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    opendp_query: OpenDPDummyQueryModel,
) -> QueryResponse:
    """
    Handles queries on dummy datasets for the OpenDP library.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object.
        opendp_query (OpenDPQueryModel): The opendp query object.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The pipeline does not contain a "measurement",
            there is not enough budget or the dataset does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        QueryResponse: A query response containing an OpenDPQueryResult.
    """
    return handle_query_on_dummy_dataset(request, opendp_query, user_name, DPLibraries.OPENDP)


@router.post(
    "/estimate_opendp_cost",
    dependencies=[Depends(server_live)],
    response_model=CostResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def estimate_opendp_cost(
    user_name: Annotated[str, Header()],
    request: Request,
    opendp_query: OpenDPRequestModel,
) -> CostResponse:
    """
    Estimates the privacy loss budget cost of an OpenDP query.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object.
        opendp_query (OpenDPRequestModel): The opendp query object.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The pipeline does not contain a "measurement",
            there is not enough budget or the dataset does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        CostResponse: The privacy loss cost of the input query.
    """
    return handle_cost_query(request, opendp_query, user_name, DPLibraries.OPENDP)


# DiffPrivLib
# -----------------------------------------------------------------------------


@router.post(
    "/diffprivlib_query",
    dependencies=[Depends(server_live)],
    response_model=QueryResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def diffprivlib_query_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    diffprivlib_query: DiffPrivLibQueryModel,
):
    """
    Handles queries for the DiffPrivLib Library.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        diffprivlib_query (DiffPrivLibQueryModel): The diffprivlib query body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        QueryResponse: A query response containing a DiffPrivLibQueryResult.
    """
    return handle_query_on_private_dataset(request, diffprivlib_query, user_name, DPLibraries.DIFFPRIVLIB)


@router.post(
    "/dummy_diffprivlib_query",
    dependencies=[Depends(server_live)],
    response_model=QueryResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_DUMMY"],
)
def dummy_diffprivlib_query_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    query_json: DiffPrivLibDummyQueryModel,
) -> QueryResponse:
    """
    Handles queries on dummy datasets for the DiffPrivLib library.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        diffprivlib_query (DiffPrivLibDummyQueryModel): The diffprivlib query body.

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        QueryResponse: A query response containing a DiffPrivLibQueryResult.
    """
    return handle_query_on_dummy_dataset(request, query_json, user_name, DPLibraries.DIFFPRIVLIB)


@router.post(
    "/estimate_diffprivlib_cost",
    dependencies=[Depends(server_live)],
    response_model=CostResponse,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
)
def estimate_diffprivlib_cost(
    user_name: Annotated[str, Header()],
    request: Request,
    diffprivlib_query: DiffPrivLibRequestModel,
) -> CostResponse:
    """
    Estimates the privacy loss budget cost of an DiffPrivLib query.

    \f
    Args:
        user_name (str): The user name.
        request (Request): Raw request object
        diffprivlib_query (DiffPrivLibRequestModel): The diffprivlib query body.
        A JSON object containing the following:
            - pipeline: The DiffPrivLib pipeline for the query.
            - feature_columns: the list of feature column to train
            - target_columns: the list of target column to predict
            - test_size: proportion of the test set
            - test_train_split_seed: seed for the random train test split,
            - imputer_strategy: imputation strategy

            Defaults to Body(example_dummy_diffprivlib).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        CostResponse: The privacy loss cost of the input query.
    """
    return handle_cost_query(request, diffprivlib_query, user_name, DPLibraries.DIFFPRIVLIB)

from typing import Annotated

from fastapi import APIRouter, Header, Request, status

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
from lomas_core.models.responses import Job
from lomas_server.routes.utils import handle_query_to_job

router = APIRouter()

# Smartnoise SQL
# -----------------------------------------------------------------------------


@router.post(
    "/smartnoise_sql_query",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def smartnoise_sql_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_sql_query: SmartnoiseSQLQueryModel,
) -> Job:
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
        Job: a scheduled Job resulting in a QueryResponse containing a SmartnoiseSQLQueryResult.
    """
    return await handle_query_to_job(request, smartnoise_sql_query, user_name, DPLibraries.SMARTNOISE_SQL)


@router.post(
    "/dummy_smartnoise_sql_query",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_DUMMY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def dummy_smartnoise_sql_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_sql_query: SmartnoiseSQLDummyQueryModel,
) -> Job:
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
        Job: a scheduled Job resulting in a QueryResponse containing a SmartnoiseSQLQueryResult.
    """
    return await handle_query_to_job(request, smartnoise_sql_query, user_name, DPLibraries.SMARTNOISE_SQL)


@router.post(
    "/estimate_smartnoise_sql_cost",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def estimate_smartnoise_sql_cost(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_sql_query: SmartnoiseSQLRequestModel,
) -> Job:
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
        Job: a scheduled Job resulting in a CostResponse containing the privacy loss cost of the input query.
    """
    return await handle_query_to_job(request, smartnoise_sql_query, user_name, DPLibraries.SMARTNOISE_SQL)


# Smartnoise Synth
# -----------------------------------------------------------------------------


@router.post(
    "/smartnoise_synth_query",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def smartnoise_synth_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_synth_query: SmartnoiseSynthQueryModel,
) -> Job:
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
        Job: a scheduled Job resulting in a QueryResponse containing a SmartnoiseSynthModel
        or SmartnoiseSynthSamples.
    """
    return await handle_query_to_job(request, smartnoise_synth_query, user_name, DPLibraries.SMARTNOISE_SYNTH)


@router.post(
    "/dummy_smartnoise_synth_query",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def dummy_smartnoise_synth_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_synth_query: SmartnoiseSynthDummyQueryModel,
) -> Job:
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
        Job: a scheduled Job resulting in a QueryResponse containing a SmartnoiseSynthModel
        or SmartnoiseSynthSamples.
    """
    return await handle_query_to_job(request, smartnoise_synth_query, user_name, DPLibraries.SMARTNOISE_SYNTH)


@router.post(
    "/estimate_smartnoise_synth_cost",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def estimate_smartnoise_synth_cost(
    user_name: Annotated[str, Header()],
    request: Request,
    smartnoise_synth_query: SmartnoiseSynthRequestModel,
) -> Job:
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
        Job: a scheduled Job resulting in a CostResponse containing the privacy loss cost of the input query.
    """
    return await handle_query_to_job(request, smartnoise_synth_query, user_name, DPLibraries.SMARTNOISE_SYNTH)


# OpenDP
# -----------------------------------------------------------------------------


@router.post(
    "/opendp_query",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def opendp_query_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    opendp_query: OpenDPQueryModel,
) -> Job:
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
        Job: a scheduled Job resulting in a QueryResponse containing an OpenDPQueryResult.
    """
    return await handle_query_to_job(request, opendp_query, user_name, DPLibraries.OPENDP)


@router.post(
    "/dummy_opendp_query",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_DUMMY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def dummy_opendp_query_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    opendp_query: OpenDPDummyQueryModel,
) -> Job:
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
        Job: a scheduled Job resulting in a QueryResponse containing an OpenDPQueryResult.
    """
    return await handle_query_to_job(request, opendp_query, user_name, DPLibraries.OPENDP)


@router.post(
    "/estimate_opendp_cost",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def estimate_opendp_cost(
    user_name: Annotated[str, Header()],
    request: Request,
    opendp_query: OpenDPRequestModel,
) -> Job:
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
        Job: a scheduled Job resulting in a CostResponse containing the privacy loss cost of the input query.
    """
    return await handle_query_to_job(request, opendp_query, user_name, DPLibraries.OPENDP)


# DiffPrivLib
# -----------------------------------------------------------------------------


@router.post(
    "/diffprivlib_query",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def diffprivlib_query_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    diffprivlib_query: DiffPrivLibQueryModel,
) -> Job:
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
        Job: a scheduled Job resulting in a QueryResponse containing a DiffPrivLibQueryResult.
    """
    return await handle_query_to_job(request, diffprivlib_query, user_name, DPLibraries.DIFFPRIVLIB)


@router.post(
    "/dummy_diffprivlib_query",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_DUMMY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def dummy_diffprivlib_query_handler(
    user_name: Annotated[str, Header()],
    request: Request,
    query_json: DiffPrivLibDummyQueryModel,
) -> Job:
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
        Job: a scheduled Job resulting in a QueryResponse containing a DiffPrivLibQueryResult.
    """
    return await handle_query_to_job(request, query_json, user_name, DPLibraries.DIFFPRIVLIB)


@router.post(
    "/estimate_diffprivlib_cost",
    response_model=Job,
    responses=SERVER_QUERY_ERROR_RESPONSES,
    tags=["USER_QUERY"],
    status_code=status.HTTP_202_ACCEPTED,
)
async def estimate_diffprivlib_cost(
    user_name: Annotated[str, Header()],
    request: Request,
    diffprivlib_query: DiffPrivLibRequestModel,
) -> Job:
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
        Job: a scheduled Job resulting in a CostResponse containing the privacy loss cost of the input query.
    """
    return await handle_query_to_job(request, diffprivlib_query, user_name, DPLibraries.DIFFPRIVLIB)

from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.responses import JSONResponse

from constants import DPLibraries
from routes.utils import (
    handle_cost_query,
    handle_query_on_dummy_dataset,
    handle_query_on_private_dataset,
    server_live,
)
from utils.query_examples import (
    example_diffprivlib,
    example_dummy_diffprivlib,
    example_dummy_opendp,
    example_dummy_smartnoise_sql,
    example_opendp,
    example_smartnoise_sql,
    example_smartnoise_sql_cost,
)
from utils.query_models import (
    DiffPrivLibModel,
    DummyDiffPrivLibModel,
    DummyOpenDPModel,
    DummySmartnoiseSQLModel,
    OpenDPModel,
    SmartnoiseSQLModel,
    SmartnoiseSQLModelCost,
)

router = APIRouter()


@router.post(
    "/smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def smartnoise_sql_handler(
    request: Request,
    query_json: SmartnoiseSQLModel = Body(example_smartnoise_sql),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Handles queries for the SmartNoiseSQL library.

    Args:
        request (Request): Raw request object
        query_json (SmartnoiseSQLModel): A JSON object containing:
            - query: The SQL query to execute. NOTE: the table name is "df",
              the query must end with "FROM df".
            - epsilon (float): Privacy parameter (e.g., 0.1).
            - delta (float): Privacy parameter (e.g., 1e-5).
            - mechanisms (dict, optional): Dictionary of mechanisms for the
              query (default: {}). See "Smartnoise-SQL mechanisms documentation
              https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms.
            - postprocess (bool, optional): Whether to postprocess the query
              results (default: True).
              See "Smartnoise-SQL postprocessing documentation
              https://docs.smartnoise.org/sql/advanced.html#postprocess.

            Defaults to Body(example_smartnoise_sql).

        user_name (str, optional): The user name.
            Defaults to Header(None).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        JSONResponse: A JSON object containing the following:
            - requested_by (str): The user name.
            - query_response (pd.DataFrame): A DataFrame containing
              the query response.
            - spent_epsilon (float): The amount of epsilon budget spent
              for the query.
            - spent_delta (float): The amount of delta budget spent
              for the query.
    """
    return handle_query_on_private_dataset(
        request, query_json, user_name, DPLibraries.SMARTNOISE_SQL
    )


# Smartnoise SQL Dummy query
@router.post(
    "/dummy_smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_smartnoise_sql_handler(
    request: Request,
    query_json: DummySmartnoiseSQLModel = Body(example_dummy_smartnoise_sql),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Handles queries on dummy datasets for the SmartNoiseSQL library.

    Args:
        request (Request): Raw request object
        query_json (DummySmartnoiseSQLModel, optional): A JSON object containing:
            - query: The SQL query to execute. NOTE: the table name is "df",
              the query must end with "FROM df".
            - epsilon (float): Privacy parameter (e.g., 0.1).
            - delta (float): Privacy parameter (e.g., 1e-5).
            - mechanisms (dict, optional): Dictionary of mechanisms for the
              query (default: {}). See Smartnoise-SQL mechanisms documentation
              https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms.
            - postprocess (bool, optional): Whether to postprocess the query
              results (default: True).
              See Smartnoise-SQL postprocessing documentation
              https://docs.smartnoise.org/sql/advanced.html#postprocess.
            - dummy (bool, optional): Whether to use a dummy dataset
              (default: False).
            - nb_rows (int, optional): The number of rows in the dummy dataset
              (default: 100).
            - seed (int, optional): The random seed for generating
              the dummy dataset (default: 42).

            Defaults to Body(example_dummy_smartnoise_sql).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.

    Returns:
        JSONResponse: A JSON object containing:
            - query_response (pd.DataFrame): a DataFrame containing
              the query response.
    """
    return handle_query_on_dummy_dataset(
        request, query_json, user_name, DPLibraries.SMARTNOISE_SQL
    )


@router.post(
    "/estimate_smartnoise_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_smartnoise_cost(
    request: Request,
    query_json: SmartnoiseSQLModelCost = Body(example_smartnoise_sql_cost),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Estimates the privacy loss budget cost of a SmartNoiseSQL query.

    Args:
        request (Request): Raw request object
        query_json (SmartnoiseSQLModelCost, optional):
            A JSON object containing the following:
            - query: The SQL query to estimate the cost for.
              NOTE: the table name is "df", the query must end with "FROM df".
            - epsilon (float): Privacy parameter (e.g., 0.1).
            - delta (float): Privacy parameter (e.g., 1e-5).
            - mechanisms (dict, optional): Dictionary of mechanisms
              for the query (default: {}).
              See Smartnoise-SQL mechanisms documentation
              https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms.

            Defaults to Body(example_smartnoise_sql_cost).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist.

    Returns:
        JSONResponse: A JSON object containing:
            - epsilon_cost (float): The estimated epsilon cost.
            - delta_cost (float): The estimated delta cost.
    """
    return handle_cost_query(
        request, query_json, user_name, DPLibraries.SMARTNOISE_SQL
    )


@router.post(
    "/opendp_query", dependencies=[Depends(server_live)], tags=["USER_QUERY"]
)
def opendp_query_handler(
    request: Request,
    query_json: OpenDPModel = Body(example_opendp),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Handles queries for the OpenDP Library.

    Args:
        request (Request): Raw request object.
        query_json (OpenDPModel, optional): A JSON object containing the following:
            - opendp_pipeline: The OpenDP pipeline for the query.
            - fixed_delta: If the pipeline measurement is of type
                "ZeroConcentratedDivergence" (e.g. with "make_gaussian") then it is
                converted to "SmoothedMaxDivergence" with "make_zCDP_to_approxDP"
                (see "opendp measurements documentation at
                https://docs.opendp.org/en/stable/api/python/opendp.combinators.html#opendp.combinators.make_zCDP_to_approxDP). # noqa # pylint: disable=C0301
                In that case a "fixed_delta" must be provided by the user.

            Defaults to Body(example_opendp).

        user_name (str, optional): The user name.
            Defaults to Header(None).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The pipeline does not contain a "measurement",
            there is not enough budget or the dataset does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        JSONResponse: A JSON object containing the following:
            - requested_by (str): The user name.
            - query_response (pd.DataFrame): A DataFrame containing
              the query response.
            - spent_epsilon (float): The amount of epsilon budget spent
              for the query.
            - spent_delta (float): The amount of delta budget spent
              for the query.
    """
    response = handle_query_on_private_dataset(
        request, query_json, user_name, DPLibraries.OPENDP
    )
    return JSONResponse(content=response)


@router.post(
    "/dummy_opendp_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_opendp_query_handler(
    request: Request,
    query_json: DummyOpenDPModel = Body(example_dummy_opendp),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Handles queries on dummy datasets for the OpenDP library.

    Args:
        request (Request): Raw request object.
        query_json (DummyOpenDPModel, optional):
            A JSON object containing the following:
            - opendp_pipeline: The OpenDP pipeline for the query.
            - fixed_delta: If the pipeline measurement is of type\
              "ZeroConcentratedDivergence" (e.g. with "make_gaussian") then
              it is converted to "SmoothedMaxDivergence" with
              "make_zCDP_to_approxDP" (see opendp measurements documentation at
              https://docs.opendp.org/en/stable/api/python/opendp.combinators.html#opendp.combinators.make_zCDP_to_approxDP). # noqa # pylint: disable=C0301
              In that case a "fixed_delta" must be provided by the user.
            - dummy (bool, optional): Whether to use a dummy dataset
              (default: False).
            - nb_rows (int, optional): The number of rows
              in the dummy dataset (default: 100).
            - seed (int, optional): The random seed for generating
              the dummy dataset (default: 42).

            Defaults to Body(example_dummy_opendp).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.

    Returns:
        JSONResponse: A JSON object containing:
            - query_response (pd.DataFrame): a DataFrame containing
              the query response.
    """
    return handle_query_on_dummy_dataset(
        request, query_json, user_name, DPLibraries.OPENDP
    )


@router.post(
    "/estimate_opendp_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_opendp_cost(
    request: Request,
    query_json: OpenDPModel = Body(example_opendp),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Estimates the privacy loss budget cost of an OpenDP query.

    Args:
        request (Request): Raw request object
        query_json (OpenDPModel, optional):
            A JSON object containing the following:
            - "opendp_pipeline": The OpenDP pipeline for the query.

            Defaults to Body(example_opendp).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The dataset does not exist or the
            pipeline does not contain a measurement.

    Returns:
        JSONResponse: A JSON object containing:
            - epsilon_cost (float): The estimated epsilon cost.
            - delta_cost (float): The estimated delta cost.
    """
    return handle_cost_query(
        request, query_json, user_name, DPLibraries.OPENDP
    )


@router.post(
    "/diffprivlib_query",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def diffprivlib_query_handler(
    request: Request,
    query_json: DiffPrivLibModel = Body(example_diffprivlib),
    user_name: str = Header(None),
):
    """
    Handles queries for the DiffPrivLib Library.

    Args:
        request (Request): Raw request object.
        query_json (OpenDPModel, optional): A JSON object containing the following:
            - pipeline: The DiffPrivLib pipeline for the query.
            - feature_columns: the list of feature column to train
            - target_columns: the list of target column to predict
            - test_size: proportion of the test set
            - test_train_split_seed: seed for the random train test split,
            - imputer_strategy: imputation strategy

            Defaults to Body(example_diffprivlib).

        user_name (str, optional): The user name.
            Defaults to Header(None).

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: The pipeline does not contain a "measurement",
            there is not enough budget or the dataset does not exist.
        UnauthorizedAccessException: A query is already ongoing for this user,
            the user does not exist or does not have access to the dataset.

    Returns:
        JSONResponse: A JSON object containing the following:
            - requested_by (str): The user name.
            - query_response (pd.DataFrame): A DataFrame containing
              the query response.
            - spent_epsilon (float): The amount of epsilon budget spent
              for the query.
            - spent_delta (float): The amount of delta budget spent
              for the query.
    """
    return handle_query_on_private_dataset(
        request, query_json, user_name, DPLibraries.DIFFPRIVLIB
    )


@router.post(
    "/dummy_diffprivlib_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_diffprivlib_query_handler(
    request: Request,
    query_json: DummyDiffPrivLibModel = Body(example_dummy_diffprivlib),
    user_name: str = Header(None),
):
    """
    Handles queries on dummy datasets for the DiffPrivLib library.

    Args:
        request (Request): Raw request object.
        query_json (DiffPrivLibModel, optional): A JSON object containing the following:
            - pipeline: The DiffPrivLib pipeline for the query.
            - feature_columns: the list of feature column to train
            - target_columns: the list of target column to predict
            - test_size: proportion of the test set
            - test_train_split_seed: seed for the random train test split,
            - imputer_strategy: imputation strategy
            - nb_rows (int, optional): The number of rows in the dummy dataset
              (default: 100).
            - seed (int, optional): The random seed for generating
              the dummy dataset (default: 42).
              Defaults to Body(example_dummy_diffprivlib)

    Raises:
        ExternalLibraryException: For exceptions from libraries
            external to this package.
        InternalServerException: For any other unforseen exceptions.
        InvalidQueryException: If there is not enough budget or the dataset
            does not exist.

    Returns:
        JSONResponse: A JSON object containing:
            - query_response (pd.DataFrame): a DataFrame containing
              the query response.
    """
    return handle_query_on_dummy_dataset(
        request, query_json, user_name, DPLibraries.DIFFPRIVLIB
    )


@router.post(
    "/estimate_diffprivlib_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_diffprivlib_cost(
    request: Request,
    query_json: DiffPrivLibModel = Body(example_diffprivlib),
    user_name: str = Header(None),
):
    """
    Estimates the privacy loss budget cost of an DiffPrivLib query.

    Args:
        request (Request): Raw request object
        query_json (DiffPrivLibModel, optional):
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
        InvalidQueryException: The dataset does not exist or the
            pipeline does not contain a measurement.

    Returns:
        JSONResponse: A JSON object containing:
            - epsilon_cost (float): The estimated epsilon cost.
            - delta_cost (float): The estimated delta cost.
    """
    return handle_cost_query(
        request, query_json, user_name, DPLibraries.DIFFPRIVLIB
    )
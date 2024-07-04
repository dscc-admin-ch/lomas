from fastapi import APIRouter, Body, Depends, Header, Request
from fastapi.responses import JSONResponse

from constants import DPLibraries
from dp_queries.dp_libraries.utils import querier_factory
from dp_queries.dummy_dataset import get_dummy_dataset_for_query
from utils.error_handler import KNOWN_EXCEPTIONS, InternalServerException
from utils.example_inputs import (
    example_dummy_opendp,
    example_dummy_smartnoise_sql,
    example_opendp,
    example_smartnoise_sql,
    example_smartnoise_sql_cost,
)
from utils.input_models import (
    DummyOpenDPInp,
    DummySNSQLInp,
    OpenDPInp,
    SNSQLInp,
    SNSQLInpCost,
)
from utils.utils import server_live

router = APIRouter()


@router.post(
    "/smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def smartnoise_sql_handler(
    _request: Request,
    query_json: SNSQLInp = Body(example_smartnoise_sql),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Handles queries for the SmartNoiseSQL library.

    Args:
        request (Request): Raw request object
        query_json (SNSQLInp): A JSON object containing:
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
    from app import app  # pylint: disable=C0415

    try:
        response = app.state.query_handler.handle_query(
            DPLibraries.SMARTNOISE_SQL, query_json, user_name
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return response


# Smartnoise SQL Dummy query
@router.post(
    "/dummy_smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_smartnoise_sql_handler(
    _request: Request,
    query_json: DummySNSQLInp = Body(example_dummy_smartnoise_sql),
) -> JSONResponse:
    """
    Handles queries on dummy datasets for the SmartNoiseSQL library.

    Args:
        request (Request): Raw request object
        query_json (DummySNSQLInp, optional): A JSON object containing:
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
    from app import app  # pylint: disable=C0415

    ds_private_dataset = get_dummy_dataset_for_query(
        app.state.admin_database, query_json
    )
    dummy_querier = querier_factory(
        DPLibraries.SMARTNOISE_SQL, private_dataset=ds_private_dataset
    )
    try:
        _ = dummy_querier.cost(query_json)  # verify cost works
        response_df = dummy_querier.query(query_json)
        response = JSONResponse(content={"query_response": response_df})
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return response


@router.post(
    "/estimate_smartnoise_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_smartnoise_cost(
    _request: Request,
    query_json: SNSQLInpCost = Body(example_smartnoise_sql_cost),
) -> JSONResponse:
    """
    Estimates the privacy loss budget cost of a SmartNoiseSQL query.

    Args:
        request (Request): Raw request object
        query_json (SNSQLInpCost, optional):
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
    from app import app  # pylint: disable=C0415

    try:
        response = app.state.query_handler.estimate_cost(
            DPLibraries.SMARTNOISE_SQL,
            query_json,
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content=response)


@router.post(
    "/opendp_query", dependencies=[Depends(server_live)], tags=["USER_QUERY"]
)
def opendp_query_handler(
    _request: Request,
    query_json: OpenDPInp = Body(example_opendp),
    user_name: str = Header(None),
) -> JSONResponse:
    """
    Handles queries for the OpenDP Library.

    Args:
        request (Request): Raw request object.
        query_json (OpenDPInp, optional): A JSON object containing the following:
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
    from app import app  # pylint: disable=C0415

    try:
        response = app.state.query_handler.handle_query(
            DPLibraries.OPENDP, query_json, user_name
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content=response)


@router.post(
    "/dummy_opendp_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_opendp_query_handler(
    _request: Request,
    query_json: DummyOpenDPInp = Body(example_dummy_opendp),
) -> JSONResponse:
    """
    Handles queries on dummy datasets for the OpenDP library.

    Args:
        request (Request): Raw request object.
        query_json (DummyOpenDPInp, optional):
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
    from app import app  # pylint: disable=C0415

    ds_private_dataset = get_dummy_dataset_for_query(
        app.state.admin_database, query_json
    )
    dummy_querier = querier_factory(
        DPLibraries.OPENDP, private_dataset=ds_private_dataset
    )

    try:
        _ = dummy_querier.cost(query_json)  # verify cost works
        response_df = dummy_querier.query(query_json)
        response = {"query_response": response_df}

    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content=response)


@router.post(
    "/estimate_opendp_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_opendp_cost(
    _request: Request,
    query_json: OpenDPInp = Body(example_opendp),
) -> JSONResponse:
    """
    Estimates the privacy loss budget cost of an OpenDP query.

    Args:
        request (Request): Raw request object
        query_json (OpenDPInp, optional):
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
    from app import app  # pylint: disable=C0415

    try:
        response = app.state.query_handler.estimate_cost(
            DPLibraries.OPENDP,
            query_json,
        )
    except KNOWN_EXCEPTIONS as e:
        raise e
    except Exception as e:
        raise InternalServerException(e) from e

    return JSONResponse(content=response)

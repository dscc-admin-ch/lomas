import io
import json

import polars as pl
from fastapi import status
from fastapi.testclient import TestClient

from app import app
from tests.test_api_root import TestSetupRootAPIEndpoint
from utils.query_examples import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    OPENDP_POLARS_PIPELINE,
    OPENDP_POLARS_PIPELINE_COVID,
    example_opendp_polars,
    example_opendp_polars_datetime,
)


def get_lf_from_json(pipeline) -> pl.LazyFrame:
    """Deserialize a JSON string to create a Polars LazyFrame.

    This function deserializes a JSON string into a Polars
    `LazyFrame`.

    Returns:
        pl.LazyFrame: The deserialized LazyFrame containing the data
        from the JSON string.
    """
    lf = pl.LazyFrame.deserialize(
        io.StringIO(pipeline), format="json"
    )

    return lf


def mean_query_serialized(lf: pl.LazyFrame):
    """Example of a mean query using OpenDP with Polars.

    This function computes the differentially private mean of the "income" column
    in the provided `LazyFrame` with specified privacy parameters, then returns
    the serialized query plan in JSON format.

    Args:
        lf (pl.LazyFrame): A Polars LazyFrame containing the data
        with at least an "income" column.

    Returns:
        dict: The serialized plan of the mean query in JSON format.
    """
    plan = lf.select(
        pl.col("income").dp.mean(bounds=(1000, 100000), scale=1000.0)
    )

    return plan.serialize(format="json")


def group_query_serialized(lf: pl.LazyFrame) -> str:
    """Example of a grouped mean query using OpenDP with Polars.

    This function computes the differentially private mean of the "income" column
    grouped by the "sex" column in the provided `LazyFrame`, and returns the
    serialized query plan in JSON format. The results are sorted by "income".

    Args:
        lf (pl.LazyFrame): A Polars LazyFrame containing the data
        with at least "income" and "sex" columns.

    Returns:
        str: The serialized plan of the grouped mean query in JSON format.
    """
    plan = (
        lf.group_by("sex")
        .agg([pl.col("income").dp.mean(bounds=(1000, 100000), scale=100.0)])
        .sort("income")
    )

    return plan.serialize(format="json")


def multiple_group_query_serialized(lf: pl.LazyFrame) -> str:
    """Example of a grouped mean query using OpenDP with Polars,
    grouped by multiple columns.

    This function computes the differentially private mean of the "income" column,
    grouped by both the "sex" and "region" columns in the provided `LazyFrame`.
    The results are then sorted by "income", and the serialized query plan is returned
    in JSON format.

    Args:
        lf (pl.LazyFrame): A Polars LazyFrame containing the data
        with at least "income", "sex", and "region" columns.

    Returns:
        str: The serialized plan of the grouped mean query in JSON format.
    """
    plan = (
        lf.group_by(["sex", "region"])
        .agg([pl.col("income").dp.mean(bounds=(1000, 100000), scale=100.0)])
        .sort("income")
    )

    return plan.serialize(format="json")


class TestOpenDpPolarsEndpoint(
    TestSetupRootAPIEndpoint
):  # pylint: disable=R0904
    """
    Test OpenDP Endpoint with different polars plans.
    """

    def test_opendp_polars_query(self) -> None:
        """Test opendp polars query"""
        with TestClient(app, headers=self.headers) as client:
            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
            json_plan = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan

            # Laplace
            response = client.post(
                "/opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK

            # Gaussian
            example_opendp_polars["mechanism"] = "gaussian"
            response = client.post(
                "/opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK
    
    def test_opendp_polars_datetime_query(self) -> None:
        """Test opendp polars query"""
        with TestClient(app, headers=self.headers) as client:
            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE_COVID)
            # json_plan = mean_query_serialized(lf)
            json_plan = lf.select(
                pl.col("temporal").dp.mean(bounds=(1, 52), scale=100.0)
            ).serialize(format="json")
            example_opendp_polars_datetime["opendp_json"] = json_plan

            # Laplace
            response = client.post(
                "/opendp_query",
                json=example_opendp_polars_datetime,
            )
            assert response.status_code == status.HTTP_200_OK
            
            example_opendp_polars_datetime["dummy_nb_rows"] = DUMMY_NB_ROWS
            example_opendp_polars_datetime["dummy_seed"] = DUMMY_SEED
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars_datetime,
            )
            assert response.status_code == status.HTTP_200_OK
            
            json_plan = (
                lf.group_by("date")
                .agg([pl.col("temporal").dp.mean(bounds=(1, 52), scale=10.0)])
                .sort("temporal")
            ).serialize(format="json")
            
            example_opendp_polars_datetime["opendp_json"] = json_plan
            response = client.post(
                "/opendp_query",
                json=example_opendp_polars_datetime,
            )
            assert response.status_code == status.HTTP_200_OK
            
    def test_opendp_polars_cost(self) -> None:
        """test_opendp_polars_cost"""
        with TestClient(app, headers=self.headers) as client:
            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
            json_plan = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan

            # Expect to work
            example_opendp_polars["mechanism"] = "laplace"
            response = client.post(
                "/estimate_opendp_cost",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] == 0

            # Check estimation works for Gaussian mechanism
            example_opendp_polars["mechanism"] = "gaussian"
            response = client.post(
                "/estimate_opendp_cost",
                json=example_opendp_polars,
            )
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["epsilon_cost"] > 0.0
            assert response_dict["delta_cost"] > 0.0

    def test_dummy_opendp_polars_query(self) -> None:
        """test_dummy_opendp_polars_query"""
        with TestClient(app, headers=self.headers) as client:
            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
            json_plan = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan

            # Expect to work
            example_opendp_polars["mechanism"] = "laplace"
            example_opendp_polars["dummy_nb_rows"] = DUMMY_NB_ROWS
            example_opendp_polars["dummy_seed"] = DUMMY_SEED
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))

            assert response_dict["query_response"]

            # Test dummy query with Gaussian mechanism
            example_opendp_polars["dummy_nb_rows"] = DUMMY_NB_ROWS
            example_opendp_polars["dummy_seed"] = DUMMY_SEED
            example_opendp_polars["mechanism"] = "gaussian"
            response = client.post(
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK
            response_dict = json.loads(response.content.decode("utf8"))
            assert response_dict["query_response"]

    def test_grouping_query(self) -> None:
        """test_dummy_opendp_polars_query with grouing"""
        with TestClient(app, headers=self.headers) as client:

            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
            json_plan = group_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan

            response = client.post(
                "/opendp_query",
                json=example_opendp_polars,
            )

            assert response.status_code == status.HTTP_200_OK

            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
            json_plan = multiple_group_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan

            response = client.post(
                "/opendp_query",
                json=example_opendp_polars,
            )
            assert response.status_code == status.HTTP_200_OK

import io
import unittest

import opendp as dp
import polars as pl
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from opendp import measures as ms

from lomas_core.error_handler import (
    InvalidQueryException,
)
from lomas_core.models.collections import Metadata
from lomas_core.models.exceptions import (
    InvalidQueryExceptionModel,
)
from lomas_core.models.requests_examples import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    OPENDP_POLARS_PIPELINE,
    OPENDP_POLARS_PIPELINE_COVID,
    example_opendp_polars,
    example_opendp_polars_datetime,
)
from lomas_core.models.responses import (
    CostResponse,
    OpenDPPolarsQueryResult,
    QueryResponse,
)
from lomas_server.app import app
from lomas_server.dp_queries.dp_libraries.opendp import (
    get_global_params,
    get_lf_domain,
    multiple_group_update_params,
)
from lomas_server.tests.test_api_root import TestSetupRootAPIEndpoint
from lomas_server.tests.utils import submit_job_wait

RAW_METADATA = {
    "max_ids": 1,
    "rows": 1,
    "censor_dims": False,
    "row_privacy": True,
    "columns": {
        "column_int": {
            "type": "int",
            "precision": 32,
            "cardinality": 4,
            "categories": [5, 6, 7, 8],
        }
    },
}


def get_lf_from_json(pipeline) -> pl.LazyFrame:
    """Deserialize a JSON string to create a Polars LazyFrame.
    This function deserializes a JSON string into a Polars
    `LazyFrame`.
    Returns:
        pl.LazyFrame: The deserialized LazyFrame containing the data
        from the JSON string.
    """
    lf = pl.LazyFrame.deserialize(io.StringIO(pipeline), format="json")

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
    plan = lf.select(pl.col("income").fill_null(0).dp.mean(bounds=(1000, 100000), scale=(1000.0, 1)))

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
    plan = lf.group_by("sex").agg([pl.col("income").dp.mean(bounds=(1000, 100000), scale=(100.0, 1))])

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
    plan = lf.group_by(["sex", "region"]).agg(
        [pl.col("income").dp.mean(bounds=(1000, 100000), scale=(100.0, 1.0))]
    )

    return plan.serialize(format="json")


class TestOpenDpPolarsEndpoint(TestSetupRootAPIEndpoint):  # pylint: disable=R0904
    """
    Test OpenDP Endpoint with different polars plans.
    """

    def test_opendp_polars_query(self) -> None:
        """Test opendp polars query"""
        for mechanism in ["laplace", "gaussian"]:
            with self.subTest(msg=mechanism):
                with TestClient(app, headers=self.headers) as client:
                    lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
                    json_plan = mean_query_serialized(lf)
                    example_opendp_polars["opendp_json"] = json_plan

                    # Laplace
                    example_opendp_polars["mechanism"] = mechanism
                    job = submit_job_wait(
                        client,
                        "/opendp_query",
                        json=example_opendp_polars,
                    )
                    assert job is not None
                    response_model = QueryResponse.model_validate(job.result)
                    assert isinstance(response_model.result, OpenDPPolarsQueryResult)

    # TODO: opendp v0.12: Adapt for datetime
    @pytest.mark.long
    def test_opendp_polars_datetime_query(self) -> None:
        """Test opendp polars query"""
        with TestClient(app, headers=self.headers) as client:
            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE_COVID)
            json_plan = lf.select(pl.col("temporal").dp.mean(bounds=(1, 52), scale=(100.0, 1))).serialize(
                format="json"
            )
            example_opendp_polars_datetime["opendp_json"] = json_plan

            # Laplace
            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars_datetime,
            )
            assert job is not None
            response_model = QueryResponse.model_validate(job.result)
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

            example_opendp_polars_datetime["dummy_nb_rows"] = DUMMY_NB_ROWS
            example_opendp_polars_datetime["dummy_seed"] = DUMMY_SEED
            job = submit_job_wait(
                client,
                "/dummy_opendp_query",
                json=example_opendp_polars_datetime,
            )
            assert job is not None
            response_model = QueryResponse.model_validate(job.result)
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

            json_plan = (
                lf.group_by("date").agg([pl.col("temporal").dp.mean(bounds=(1, 52), scale=(10.0, 1))])
            ).serialize(format="json")

            example_opendp_polars_datetime["opendp_json"] = json_plan
            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars_datetime,
            )
            assert job is not None
            response_model = QueryResponse.model_validate(job.result)
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

            # grouping of grouping should not work, should raise exception
            plan = lf.group_by(["date", "georegion"]).agg(
                [pl.col("temporal").dp.mean(bounds=(1, 52), scale=(1.0, 1)).alias("avg_temp")]
            )
            plan_2 = plan.group_by("georegion").agg([pl.col("avg_temp").dp.sum((1, 2000))])
            json_plan = plan_2.serialize(format="json")
            example_opendp_polars_datetime["opendp_json"] = json_plan
            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars_datetime,
            )
            assert job is not None and job.status == "failed"
            assert job.status_code == status.HTTP_400_BAD_REQUEST
            assert job.error == InvalidQueryExceptionModel(
                message="Your are trying to do multiple groupings. "
                + "This is currently not supported, please use one grouping"
            )

    def test_opendp_polars_cost(self) -> None:
        """test_opendp_polars_cost"""
        for mechanism, delta_check in [("laplace", lambda x: x == 0), ("gaussian", lambda x: x > 0)]:
            with self.subTest(msg=mechanism):
                with TestClient(app, headers=self.headers) as client:
                    lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
                    json_plan = mean_query_serialized(lf)
                    example_opendp_polars["opendp_json"] = json_plan

                    # Expect to work
                    example_opendp_polars["mechanism"] = mechanism
                    job = submit_job_wait(client, "/estimate_opendp_cost", json=example_opendp_polars)
                    assert job is not None
                    response_model = CostResponse.model_validate(job.result)
                    assert response_model.epsilon > 0.0
                    assert delta_check(response_model.delta)

    def test_dummy_opendp_polars_query(self) -> None:
        """test_dummy_opendp_polars_query"""
        for mechanism in ["laplace", "gaussian"]:
            with self.subTest(msg=mechanism):
                with TestClient(app, headers=self.headers) as client:
                    lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
                    json_plan = mean_query_serialized(lf)
                    example_opendp_polars["opendp_json"] = json_plan

                    # Expect to work
                    example_opendp_polars["mechanism"] = mechanism
                    example_opendp_polars["dummy_nb_rows"] = DUMMY_NB_ROWS
                    example_opendp_polars["dummy_seed"] = DUMMY_SEED
                    job = submit_job_wait(
                        client,
                        "/dummy_opendp_query",
                        json=example_opendp_polars,
                    )
                    assert job is not None
                    response_model = QueryResponse.model_validate(job.result)
                    assert isinstance(response_model.result, OpenDPPolarsQueryResult)

    def test_grouping_query(self) -> None:
        """test_dummy_opendp_polars_query with grouing"""
        with TestClient(app, headers=self.headers) as client:

            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
            json_plan = group_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            assert job is not None
            response_model = QueryResponse.model_validate(job.result)
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

            lf = get_lf_from_json(OPENDP_POLARS_PIPELINE)
            json_plan = multiple_group_query_serialized(lf)
            example_opendp_polars["opendp_json"] = json_plan

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            assert job is not None
            response_model = QueryResponse.model_validate(job.result)
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)


class TestOpenDPpolarsFunctions(unittest.TestCase):  # pylint: disable=R0904
    """
    Test OpenDP Polars functions.
    """

    def test1_margin(self) -> None:
        """Test margins created"""

        RAW_METADATA["rows"] = 100
        metadata = dict(Metadata.model_validate(RAW_METADATA))
        by_config = ["column_int"]
        margin_params = get_global_params(metadata)
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)

        # Since no max_partition length: rows is taken
        # Since no max_num_partitions: cardinality is taken
        expected_margin = {"max_num_partitions": 4, "max_partition_length": 100}
        self.assertEqual(margin_params, expected_margin)

        # max_partition_length is given: then we use it instead of rows
        metadata["columns"]["column_int"].max_partition_length = 50
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_partition_length"] = 50
        self.assertEqual(margin_params, expected_margin)

        metadata["columns"]["column_int"].max_influenced_partitions = 1
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_influenced_partitions"] = 1
        self.assertEqual(margin_params, expected_margin)

        metadata["columns"]["column_int"].max_partition_contributions = 1
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_partition_contributions"] = 1
        self.assertEqual(margin_params, expected_margin)

        # Minimum between max_ids and max_partition_contributions should be taken
        metadata["columns"]["column_int"].max_partition_contributions = 4
        metadata["max_ids"] = 2
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_partition_contributions"] = 2
        self.assertEqual(margin_params, expected_margin)

    def test2_margin_grouping(self) -> None:
        """Test margins with grouping"""
        RAW_METADATA["rows"] = 100
        metadata = dict(Metadata.model_validate(RAW_METADATA))
        margin_params = get_global_params(metadata)

        # Test multi grouping
        new_col = {"type": "int", "precision": 32, "upper": 100, "lower": 1}
        RAW_METADATA["columns"]["new_col"] = new_col  # type: ignore[index]
        metadata = dict(Metadata.model_validate(RAW_METADATA))
        by_config = ["column_int", "new_col"]
        metadata["columns"]["column_int"].max_partition_length = None
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin = {
            "max_num_partitions": 4,  # from col_int cardinality
            "max_partition_length": 100,  # since all are none, rows taken
        }  # from max_ids
        self.assertEqual(margin_params, expected_margin)

        metadata["columns"]["column_int"].max_partition_length = 30
        metadata["columns"]["new_col"].max_partition_length = 50
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_partition_length"] = 30  # min between two col
        self.assertEqual(margin_params, expected_margin)

        # Check max_influenced_partitions (max should be multiple of each group)
        metadata["max_ids"] = 20
        metadata["columns"]["column_int"].max_influenced_partitions = 3
        metadata["columns"]["new_col"].max_influenced_partitions = 5
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_influenced_partitions"] = 15
        self.assertEqual(margin_params, expected_margin)

        # Should never be bigger than max_ids global
        metadata["max_ids"] = 10
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_influenced_partitions"] = 10
        self.assertEqual(margin_params, expected_margin)

        # Test multi grouping (cardinality)
        new_col_str = {"type": "string", "cardinality": 2, "categories": ["a", "b"]}
        RAW_METADATA["columns"]["new_col_str"] = new_col_str  # type: ignore[index]
        metadata = dict(Metadata.model_validate(RAW_METADATA))
        by_config = ["column_int", "new_col_str"]
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        # Since card1 = 4 and card2 = 2, card_tot = 8
        expected_margin = {
            "max_num_partitions": 8,
            "max_partition_length": 100,  # Since none for col_str
            "max_influenced_partitions": 1,  # max_ids
        }
        self.assertEqual(margin_params, expected_margin)

        # Check max_partition_contributions
        metadata["max_ids"] = 10
        metadata["columns"]["column_int"].max_partition_contributions = 5
        metadata["columns"]["new_col"].max_partition_contributions = 4
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_partition_contributions"] = 5
        self.assertEqual(margin_params, expected_margin)

        # Check max_partition_contributions (should never be bigger than max_ids)
        metadata["max_ids"] = 2
        margin_params = multiple_group_update_params(metadata, by_config, margin_params)
        expected_margin["max_partition_contributions"] = 2
        self.assertEqual(margin_params, expected_margin)

    def test3_lf_domain(self) -> None:
        """Test lazyframe with different types"""
        by_config = []  # type: ignore
        col_int = {"column_int": {"type": "int", "precision": 32, "upper": 100, "lower": 1}}
        RAW_METADATA["columns"] = col_int  # type: ignore[index]
        metadata = dict(Metadata.model_validate(RAW_METADATA))
        margin_params = get_global_params(metadata)
        # lf with int
        expected_series_type = ms.i32
        expected_series_bounds = None
        expected_series_nullable = False
        expected_series_domain = dp.domains.series_domain(
            "column_int",
            dp.domains.atom_domain(
                T=expected_series_type, nullable=expected_series_nullable, bounds=expected_series_bounds
            ),
        )
        expected_lf_domain = dp.domains.with_margin(
            dp.domains.lazyframe_domain([expected_series_domain]),
            by=by_config,
            public_info="lengths",
            **margin_params,
        )
        plan = get_lf_from_json(OPENDP_POLARS_PIPELINE)
        lf_domain = get_lf_domain(metadata, plan)
        self.assertEqual(lf_domain, expected_lf_domain)

        # lf with datetime
        # TODO 392: Adapt this test with v0.12 datetime
        col_datetime = {"col_datetime": {"type": "datetime", "upper": "2050-01-01", "lower": "1900-01-01"}}
        RAW_METADATA["columns"] = col_datetime  # type: ignore[index]
        metadata = dict(Metadata.model_validate(RAW_METADATA))

        expected_series_type = ms.String
        expected_series_domain = dp.domains.series_domain(
            "col_datetime",
            dp.domains.atom_domain(
                T=expected_series_type, nullable=expected_series_nullable, bounds=expected_series_bounds
            ),
        )
        expected_lf_domain = dp.domains.with_margin(
            dp.domains.lazyframe_domain([expected_series_domain]),
            by=by_config,
            public_info="lengths",
            **margin_params,
        )
        lf_domain = get_lf_domain(metadata, plan)
        self.assertEqual(lf_domain, expected_lf_domain)

        # Test that unknown type raises an error
        metadata["columns"]["col_datetime"].type = "new_type"
        with self.assertRaises(InvalidQueryException):
            get_lf_domain(metadata, plan)

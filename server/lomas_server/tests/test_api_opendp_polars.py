import io
from base64 import b64encode

import opendp.prelude as dp
import polars as pl
import pytest
from fastapi.testclient import TestClient

from lomas_core.models.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_core.models.exceptions import InvalidQueryExceptionModel
from lomas_core.models.requests_examples import (
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
from lomas_server.tests.test_api_root import TestSetupRootAPIEndpoint
from lomas_server.tests.utils import submit_job_wait


def deserialize_bytes_plan(pipeline: bytes) -> pl.LazyFrame:
    """Deserialize a JSON string to create a Polars LazyFrame.

    This function deserializes a JSON string into a Polars `LazyFrame`.

    Returns:
        pl.LazyFrame: The deserialized LazyFrame containing the data from the JSON string.
    """
    return pl.LazyFrame.deserialize(io.BytesIO(pipeline))


def mean_query_serialized(lf: pl.LazyFrame) -> bytes:
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
    plan = lf.select(pl.col("income").fill_null(0).fill_nan(0).dp.mean(bounds=(1000, 100000)))

    return plan.serialize()


def group_query_serialized(lf: pl.LazyFrame) -> bytes:
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
    plan = lf.group_by("sex").agg([pl.col("income").dp.mean(bounds=(1000, 100000))])

    return plan.serialize()


def multiple_group_query_serialized(lf: pl.LazyFrame) -> bytes:
    """Example of a grouped mean query using OpenDP with Polars,.

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
    plan = lf.group_by(["sex", "region"]).agg([pl.col("income").dp.mean(bounds=(1000, 100000))])

    return plan.serialize()


def context_count(lf: pl.LazyFrame) -> bytes:
    """Simple OpendPolars plan with dummy context."""
    # here context should be a function building the margin based on the metadata
    context = dp.Context.compositor(
        data=lf,
        privacy_unit=dp.unit_of(contributions=1),
        privacy_loss=dp.loss_of(epsilon=100.0),
        split_evenly_over=1,
    )

    plan = context.query().select(dp.len())

    return plan.serialize()


class TestContext(TestSetupRootAPIEndpoint):
    """Test OpenDP Endpoint with context."""

    def test_context_polars(self) -> None:
        """Test opendp polars query."""
        with TestClient(app, headers=self.headers) as client:
            # Logic with context
            # 1. In client: user create a context based on metadata and dummy dataset
            #   (done via Lomas api //i.e. "make_dummy_context")
            # 2. In client: user defines query (Context.query()....)
            # 3. Client to server: User sends pipeline to server (serialized)
            # 4. In server: Create new context based real/dummy data
            # 5. In server: deserialize context back to LazyframeQuery
            #    (context.deserialize_polars_plan(serialized_plan))
            # 6. In server: release and sent back collect() to user

            lf = deserialize_bytes_plan(OPENDP_POLARS_PIPELINE)
            plan_bytes = context_count(lf)
            example_opendp_polars["opendp_json"] = b64encode(plan_bytes).decode("utf-8")

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            response_model = QueryResponse.model_validate(job.result)
            assert response_model.epsilon > 0.0
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)


class TestOpenDpPolarsEndpoint(TestSetupRootAPIEndpoint):
    """Test OpenDP Endpoint with different polars plans."""

    def test_opendp_polars_query(self) -> None:
        """Test opendp polars query."""
        with TestClient(app, headers=self.headers) as client:
            lf = deserialize_bytes_plan(OPENDP_POLARS_PIPELINE)
            plan_bytes = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = b64encode(plan_bytes).decode("utf-8")

            # Laplace
            example_opendp_polars["epsilon"] = 1
            example_opendp_polars["rho"] = None
            example_opendp_polars["delta"] = 1e-6
            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )

            response_model = QueryResponse.model_validate(job.result)
            # print(response_model.result)
            assert response_model.epsilon > 0.0
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

            # Gaussian
            example_opendp_polars["epsilon"] = None
            example_opendp_polars["rho"] = 0.5
            example_opendp_polars["delta"] = 0.000001

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            response_model = QueryResponse.model_validate(job.result)
            assert response_model.epsilon > 0.5
            assert response_model.delta == 0.000001
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

    @pytest.mark.long
    def test_opendp_polars_datetime_query(self) -> None:
        """Test opendp polars query."""
        with TestClient(app, headers=self.headers) as client:
            lf = deserialize_bytes_plan(OPENDP_POLARS_PIPELINE_COVID)

            datetime_plan = (
                lf.with_columns(YEAR=pl.col.date.dt.year(), MONTH=pl.col.date.dt.month())
                .group_by("YEAR")
                .agg(dp.len())
            ).serialize()

            example_opendp_polars_datetime["opendp_json"] = b64encode(datetime_plan).decode("utf-8")
            example_opendp_polars_datetime["epsilon"] = 10  # enough budget to get results

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars_datetime,
            )

            response_model = QueryResponse.model_validate(job.result)
            assert (
                response_model.result.value.shape[0] >= 1
            )  # depending on noise, 2022 can be removed from result (1 or 2 rows in result)
            assert response_model.epsilon > 0.0
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

            # grouping of grouping should not work, should raise exception
            plan = lf.group_by(["date", "georegion"]).agg(
                [pl.col("temporal").dp.mean(bounds=(1, 52)).alias("avg_temp")]
            )
            plan_2 = plan.group_by("georegion").agg([pl.col("avg_temp").dp.sum((1, 2000))])
            plan_bytes = plan_2.serialize()
            example_opendp_polars_datetime["opendp_json"] = b64encode(plan_bytes).decode("utf-8")
            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars_datetime,
            )
            assert job.status == "failed"
            # assert job.status_code == status.HTTP_400_BAD_REQUEST
            # assert job.error == InvalidQueryExceptionModel(
            #     message="Your are trying to do multiple groupings. "
            #     + "This is currently not supported, please use one grouping"
            # )

    def test_opendp_polars_cost(self) -> None:
        """Test_opendp_polars_cost."""
        with TestClient(app, headers=self.headers) as client:
            lf = deserialize_bytes_plan(OPENDP_POLARS_PIPELINE)
            plan_bytes = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = b64encode(plan_bytes).decode("utf-8")

            # Laplace (MaxDivergence)
            example_opendp_polars["epsilon"] = 1
            example_opendp_polars["delta"] = None
            example_opendp_polars["rho"] = None
            job = submit_job_wait(client, "/estimate_opendp_cost", json=example_opendp_polars)
            response_model = CostResponse.model_validate(job.result)
            assert response_model.epsilon == 1
            assert response_model.delta == 0

            # Laplace (Approx MaxDivergence)
            example_opendp_polars["epsilon"] = 1
            example_opendp_polars["delta"] = 1e-6
            example_opendp_polars["rho"] = None
            job = submit_job_wait(client, "/estimate_opendp_cost", json=example_opendp_polars)
            response_model = CostResponse.model_validate(job.result)
            assert response_model.epsilon == 1
            assert response_model.delta == 1e-6

            # Gaussian (Approx zCDP)
            example_opendp_polars["epsilon"] = None
            example_opendp_polars["rho"] = 2
            example_opendp_polars["delta"] = 0.000001
            job = submit_job_wait(client, "/estimate_opendp_cost", json=example_opendp_polars)
            response_model = CostResponse.model_validate(job.result)
            assert response_model.epsilon > 2
            assert response_model.delta == 0.000001

            # Gaussian (zCDP)
            example_opendp_polars["epsilon"] = None
            example_opendp_polars["rho"] = 2
            example_opendp_polars["delta"] = 1e-6
            job = submit_job_wait(client, "/estimate_opendp_cost", json=example_opendp_polars)
            response_model = CostResponse.model_validate(job.result)
            assert response_model.epsilon > 2
            assert response_model.delta == 1e-6

            # zCDP without specifying a user-defined delta should fail
            example_opendp_polars["delta"] = None
            job = submit_job_wait(client, "/estimate_opendp_cost", json=example_opendp_polars)
            assert job.error == InvalidQueryExceptionModel(message="Provide a fixed delta for this query.")

    def test_dummy_opendp_polars_query(self) -> None:
        """Test_dummy_opendp_polars_query."""
        with TestClient(app, headers=self.headers) as client:
            lf = deserialize_bytes_plan(OPENDP_POLARS_PIPELINE)
            plan_bytes = mean_query_serialized(lf)
            example_opendp_polars["opendp_json"] = b64encode(plan_bytes).decode("utf-8")

            # Expect to work
            example_opendp_polars["dummy_nb_rows"] = DUMMY_NB_ROWS
            example_opendp_polars["dummy_seed"] = DUMMY_SEED
            job = submit_job_wait(
                client,
                "/dummy_opendp_query",
                json=example_opendp_polars,
            )
            response_model = QueryResponse.model_validate(job.result)
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

    def test_grouping_query(self) -> None:
        """Test_opendp_polars_query with grouing."""
        with TestClient(app, headers=self.headers) as client:
            lf = deserialize_bytes_plan(OPENDP_POLARS_PIPELINE)
            plan_bytes = group_query_serialized(lf)
            example_opendp_polars["opendp_json"] = b64encode(plan_bytes).decode("utf-8")

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            response_model = QueryResponse.model_validate(job.result)
            assert response_model.epsilon > 0.0
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

    def test_polars_features(self) -> None:
        """Test_opendp_polars_query with different polars features (cut, filter, n_unique)."""
        with TestClient(app, headers=self.headers) as client:
            lf = deserialize_bytes_plan(OPENDP_POLARS_PIPELINE)
            example_opendp_polars["epsilon"] = 1
            example_opendp_polars["delta"] = 1e-6
            example_opendp_polars["rho"] = None

            # Polars plan with cut feature
            plan_bytes = (
                lf.with_columns(
                    pl.col.income.cut(breaks=[4_000, 5_000, 6_000, 7_000], left_closed=True).alias(
                        "binned_income"
                    )
                )
                .group_by(pl.col.binned_income)
                .agg(dp.len())
                .serialize()
            )

            example_opendp_polars["opendp_json"] = b64encode(plan_bytes).decode("utf-8")

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            response_model = QueryResponse.model_validate(job.result)
            assert response_model.result.value.shape[0] == 4
            assert response_model.epsilon > 0.0
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)

            # delta = None => query fails ?

            # Polars plan with filter
            plan_ecobranch = (
                lf.with_columns(pl.col.eco_branch.cast(str))
                .filter(pl.col.eco_branch == "25")
                .select(pl.col.income.fill_null(0).fill_nan(0).dp.len())
                .serialize()
            )

            example_opendp_polars["opendp_json"] = b64encode(plan_ecobranch).decode("utf-8")

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            response_model = QueryResponse.model_validate(job.result)
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)
            assert response_model.result.value.shape[0] > 0

            ## Polars plan with n_unique
            plan_nunique = lf.select(pl.col.eco_branch.dp.n_unique()).serialize()
            example_opendp_polars["opendp_json"] = b64encode(plan_nunique).decode("utf-8")

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            response_model = QueryResponse.model_validate(job.result)
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)
            assert response_model.result.value.shape[0] > 0

    def test_multiple_grouping_query(self) -> None:
        """Test_opendp_polars query with multiple grouping."""
        with TestClient(app, headers=self.headers) as client:
            lf = deserialize_bytes_plan(OPENDP_POLARS_PIPELINE)
            plan_bytes = multiple_group_query_serialized(lf)
            example_opendp_polars["opendp_json"] = b64encode(plan_bytes).decode("utf-8")

            job = submit_job_wait(
                client,
                "/opendp_query",
                json=example_opendp_polars,
            )
            response_model = QueryResponse.model_validate(job.result)
            assert response_model.epsilon > 0.0
            assert isinstance(response_model.result, OpenDPPolarsQueryResult)


# TODO: create tests based on new function build_margins_from_metadata

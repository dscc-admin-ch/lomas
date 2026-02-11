from dataclasses import dataclass

import numpy as np
import opendp.prelude as dp
import pandas as pd
import polars as pl
import pytest
from diffprivlib import models
from oauthlib import oauth2
from sklearn.pipeline import Pipeline

from lomas_client import Client
from lomas_client.constants import DEFAULT_EPSILON
from lomas_core.error_handler import UnauthorizedAccessException
from lomas_core.models.responses import OpenDPPolarsQueryResult
from lomas_server.administration.dex.dex_admin import (
    add_dex_user,
    del_all_dex_users,
)
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup
from lomas_server.models.config import AdminConfig


@pytest.fixture
def demo_setup():
    lomas_demo_setup()


@dataclass(frozen=True)
class Aria:
    user_name: str = "aria"
    user_email: str = "aria.stark@winterfell.no"
    user_password: str = "secret_aria"

    def as_client(self, dataset_name="anyName") -> Client:
        return Client(user_name=self.user_email, user_password=self.user_password, dataset_name=dataset_name)


@pytest.fixture
def aria():
    return Aria()


@pytest.fixture
def dex_config():
    """Dex config.

    Removes all dex users before yield.
    """
    admin_config = AdminConfig()
    dex_config = admin_config.dex_config
    assert dex_config is not None
    # Cleanup for tests
    del_all_dex_users(dex_config)

    yield dex_config

    # Cleanup: delete all users to start fresh
    del_all_dex_users(dex_config)


def test_missing_configs() -> None:
    with pytest.raises(ValueError, match=r"Missing client config parameters"):
        Client()


def test_oauth2(aria, dex_config) -> None:
    with pytest.raises(oauth2.AccessDeniedError, match=r"Invalid username or password"):
        aria.as_client()

    # Add a user
    add_dex_user(dex_config, aria.user_name, aria.user_email, aria.user_password)

    client = aria.as_client()

    with pytest.raises(UnauthorizedAccessException, match=f"User {aria.user_name} does not exist"):
        client.get_dataset_metadata()


def test_oauth2_demo(dex_config, demo_setup) -> None:
    user_name = "Jack"
    client = Client(
        user_name=f"{user_name}@example.com", user_password=user_name.lower(), dataset_name="TITANIC"
    )

    init_budget = client.get_initial_budget()
    assert init_budget.initial_delta == 0.2
    assert init_budget.initial_epsilon == 45

    assert set(client.get_dataset_metadata().keys()) == {
        "censor_dims",
        "columns",
        "max_ids",
        "rows",
        "row_privacy",
        "clamp_columns",
        "clamp_counts",
        "use_dpsu",
    }

    df_dummy = client.get_dummy_dataset()
    assert df_dummy.shape == (100, 8)

    df_dummy_lz = client.get_dummy_dataset(lazy=True)
    assert df_dummy_lz.collect().shape == (100, 8)

    ## Dummy Query
    plan = df_dummy_lz.select(pl.col("Age").dp.mean(bounds=(0, 100), scale=10), dp.len(scale=10))
    dummy_res = client.opendp.query(plan, dummy=True)
    assert isinstance(dummy_res.result.value, pl.DataFrame)

    avg_age = dummy_res.result.value.to_pandas().Age[0]
    assert avg_age == pytest.approx(51.5, 0.5)

    rem_budget = client.get_remaining_budget()
    assert rem_budget.remaining_delta == 0.2
    assert rem_budget.remaining_epsilon == 45
    tot_spent = client.get_total_spent_budget()
    assert tot_spent.total_spent_delta == 0
    assert tot_spent.total_spent_epsilon == 0

    # True Query
    res = client.opendp.query(plan)
    assert isinstance(res.result.value, pl.DataFrame)

    avg_age = res.result.value.to_pandas().Age[0]
    assert avg_age == pytest.approx(51.5, 0.5)

    rem_budget = client.get_remaining_budget()
    assert rem_budget.remaining_delta == pytest.approx(0.2, 1e-3)
    assert rem_budget.remaining_epsilon == pytest.approx(35, 1)
    tot_spent = client.get_total_spent_budget()
    assert tot_spent.total_spent_delta == pytest.approx(0, abs=1e-3)
    assert tot_spent.total_spent_epsilon == pytest.approx(10, 1)

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 1
    assert prev_queries[0]["dataset_name"] == "TITANIC"
    assert prev_queries[0]["dp_library"] == "opendp"


def test_demo_diffprivlib(dex_config, demo_setup) -> None:
    user_name = "Dr.Antartica"
    client = Client(
        user_name=f"{user_name.lower()}@example.com", user_password=user_name.lower(), dataset_name="PENGUIN"
    )

    penguin_metadata = client.get_dataset_metadata()
    feature_columns = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
    target_columns = ["species"]
    bounds = (
        [penguin_metadata["columns"][feature]["lower"] for feature in feature_columns],
        [penguin_metadata["columns"][feature]["upper"] for feature in feature_columns],
    )
    data_norm = np.sqrt(np.linalg.norm(bounds[1]))

    dpl_pipeline = Pipeline(
        [
            ("scaler", models.StandardScaler(epsilon=0.5, bounds=bounds)),
            ("classifier", models.LogisticRegression(epsilon=1.0, data_norm=data_norm)),
        ]
    )

    dummy_response = client.diffprivlib.query(
        pipeline=dpl_pipeline, feature_columns=feature_columns, target_columns=target_columns, dummy=True
    )

    assert dummy_response.result.model is not None

    feature_columns = ["bill_length_mm"]
    target_columns = ["bill_depth_mm"]
    bill_length_meta = penguin_metadata["columns"]["bill_length_mm"]
    bill_depth_meta = penguin_metadata["columns"]["bill_depth_mm"]
    dpl_pipeline = Pipeline(
        [
            (
                "lr",
                models.LinearRegression(
                    epsilon=2.0,
                    bounds_X=(bill_length_meta["lower"], bill_length_meta["upper"]),
                    bounds_y=(bill_depth_meta["lower"], bill_depth_meta["upper"]),
                ),
            ),
        ]
    )
    cost_res = client.diffprivlib.cost(
        dpl_pipeline,
        feature_columns=feature_columns,
        target_columns=target_columns,
        imputer_strategy="drop",
    )
    assert cost_res.epsilon == pytest.approx(2, 0.1)
    assert cost_res.delta == pytest.approx(0, abs=1e-4)
    response = client.diffprivlib.query(
        pipeline=dpl_pipeline, feature_columns=feature_columns, target_columns=target_columns
    )
    model = response.result.model
    predictions = model.predict(
        pd.DataFrame(
            {
                "bill_length_mm": [bill_length_meta["lower"], bill_length_meta["upper"]],
            }
        )
    )

    assert len(predictions) == 2
    assert predictions == pytest.approx([20, 20], abs=20)

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 1
    assert prev_queries[0]["dataset_name"] == "PENGUIN"
    assert prev_queries[0]["dp_library"] == "diffprivlib"
    returned_model = prev_queries[0]["response"]["result"]["model"]
    predictions = returned_model.predict(
        pd.DataFrame(
            {
                "bill_length_mm": [bill_length_meta["lower"], bill_length_meta["upper"]],
            }
        )
    )

    assert len(predictions) == 2
    assert predictions == pytest.approx([20, 20], abs=20)


@pytest.mark.long
@pytest.mark.skip(reason="waiting on OpenDP 0.14 synth")
def test_demo_smartnoise_synth(dex_config, demo_setup) -> None:
    user_name = "Dr.Antartica"
    client = Client(
        user_name=f"{user_name.lower()}@example.com", user_password=user_name.lower(), dataset_name="PENGUIN"
    )

    cost_res = client.smartnoise_synth.cost(
        synth_name="aim",
        epsilon=1.0,
        delta=0.0001,
        select_cols=["species", "island"],
    )
    assert cost_res.epsilon == pytest.approx(1, 0.05)
    assert cost_res.delta == pytest.approx(1e-4, abs=5e-5)

    for dummy in [True, False]:
        res = client.smartnoise_synth.query(
            synth_name="dpgan",
            epsilon=1.0,
            condition="body_mass_g > 5000",
            nb_samples=10,
            dummy=dummy,
        )
        res_df = res.result.df_samples
        assert res_df.flipper_length_mm.mean() == pytest.approx(200, 0.25)
        assert res_df.body_mass_g.min() >= 5000

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 1
    assert prev_queries[0]["dataset_name"] == "PENGUIN"
    assert prev_queries[0]["dp_library"] == "smartnoise_synth"
    response_archives = prev_queries[0]["response"]
    assert response_archives["epsilon"] == 1.0
    assert response_archives["delta"] >= 0.0


def test_demo_opendp_polars(dex_config, demo_setup) -> None:
    user_name = "Dr.FSO"
    client = Client(
        user_name=f"{user_name.lower()}@example.com",
        user_password=user_name.lower(),
        dataset_name="FSO_INCOME_SYNTHETIC",
    )
    income_metadata = client.get_dataset_metadata()
    NB_ROWS, SEED = 200, 0
    context = client.get_context(nb_rows=NB_ROWS, seed=SEED, epsilon=DEFAULT_EPSILON)
    test = client.get_dummy_dataset(nb_rows=NB_ROWS, seed=SEED)
    assert len(test.dtypes) >= 5

    income_lower_bound, income_upper_bound = (
        income_metadata["columns"]["income"]["lower"],
        income_metadata["columns"]["income"]["upper"],
    )
    plan = context.query().select(pl.col("income").dp.mean(bounds=(income_lower_bound, income_upper_bound)))
    query_res = client.opendp.query(plan, nb_rows=NB_ROWS, seed=SEED)
    assert query_res.epsilon == DEFAULT_EPSILON
    assert isinstance(query_res.result, OpenDPPolarsQueryResult)
    df_polar = query_res.result.value
    assert df_polar.shape == (1, 1)

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 1
    assert prev_queries[0]["dataset_name"] == "FSO_INCOME_SYNTHETIC"
    assert prev_queries[0]["dp_library"] == "opendp"
    response_archives = prev_queries[0]["response"]
    assert response_archives["epsilon"] == DEFAULT_EPSILON
    assert response_archives["delta"] == 0.0

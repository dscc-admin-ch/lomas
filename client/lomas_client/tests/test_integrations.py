from dataclasses import dataclass

import numpy as np
import pandas as pd
import polars as pl
import pytest
from diffprivlib import models
from mantelo import KeycloakAdmin
from returns.io import IOResultE, IOSuccess, impure_safe
from returns.pipeline import flow
from returns.pointfree import map_
from returns.unsafe import unsafe_perform_io
from sklearn.pipeline import Pipeline

from lomas_client import ClientIO
from lomas_core.models.responses import OpenDPPolarsQueryResult
from lomas_server.administration.keycloak_admin import (
    add_kc_user,
    del_all_kc_users,
    get_kc_admin,
)
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup
from lomas_server.models.config import AdminConfig, KeycloakClientConfig


@pytest.fixture
@impure_safe
def demo_setup() -> IOResultE:
    lomas_demo_setup()


@dataclass(frozen=True)
class Aria:
    user_name: str = "aria"
    user_email: str = "aria.stark@winterfell.no"
    client_secret: str = "secret_aria"

    def as_client(self, dataset_name="anyName") -> ClientIO:
        return ClientIO(client_id=self.user_name, client_secret=self.client_secret, dataset_name=dataset_name)


@pytest.fixture
def aria():
    return Aria()


@dataclass(frozen=True)
class KC:
    config: KeycloakClientConfig
    admin: KeycloakAdmin


@pytest.fixture
def kc():
    """Connection to keycloak."""
    admin_config = AdminConfig()
    kc_config = admin_config.kc_config
    assert kc_config is not None

    yield KC(kc_config, get_kc_admin(kc_config))

    # Cleanup: delete all users to start fresh
    del_all_kc_users(kc_config)


def test_missing_configs() -> None:
    with pytest.raises(ValueError, match=r"Missing one of or invalid:"):
        ClientIO()


def test_oauth2(aria, kc) -> None:
    client = aria.as_client()
    assert client.get_dataset_metadata().failure()

    # Add a user
    add_kc_user(kc.config, aria.user_name, aria.user_email, aria.client_secret)

    client = aria.as_client()

    # with pytest.raises(UnauthorizedAccessException, match=f"User {aria.user_name} does not exist"):
    # client.get_dataset_metadata()
    metadata = client.get_dataset_metadata()
    assert metadata.failure()


def test_oauth2_demo(kc, demo_setup: IOResultE) -> None:
    user_name = "Jack"
    client = ClientIO(client_id=user_name, client_secret=user_name.lower(), dataset_name="TITANIC")

    init_budget = client.get_initial_budget()
    assert isinstance(init_budget, IOSuccess)
    assert init_budget.map(lambda x: x.initial_delta) == IOSuccess(0.2)
    assert init_budget.map(lambda x: x.initial_epsilon) == IOSuccess(45)

    assert client.get_dataset_metadata().map(set) == IOSuccess(
        {
            "censor_dims",
            "columns",
            "max_ids",
            "rows",
            "row_privacy",
            "clamp_columns",
            "clamp_counts",
            "use_dpsu",
        }
    )

    df_dummy = client.get_dummy_dataset()
    assert df_dummy.map(lambda x: x.shape) == IOSuccess((100, 11))

    df_dummy_lz = client.get_dummy_dataset(lazy=True)
    assert df_dummy_lz.map(lambda x: x.collect().shape) == IOSuccess((100, 11))

    # Smartnoise

    ## Dummy Query
    query = "SELECT COUNT(*) AS nb_passengers, AVG(Age) AS avg_age FROM df"
    dummy_res = client.smartnoise_sql.query(query=query, epsilon=100, delta=2, dummy=True)

    avg_age = dummy_res.map(lambda x: x.result.df["avg_age"][0])
    assert avg_age == IOSuccess(pytest.approx(51.5, 0.5))

    rem_budget = client.get_remaining_budget()
    assert rem_budget.map(lambda x: x.remaining_delta) == IOSuccess(0.2)
    assert rem_budget.map(lambda x: x.remaining_epsilon) == IOSuccess(45)
    tot_spent = client.get_total_spent_budget()
    assert tot_spent.map(lambda x: x.total_spent_delta) == IOSuccess(0)
    assert tot_spent.map(lambda x: x.total_spent_epsilon) == IOSuccess(0)

    # True Query
    res = client.smartnoise_sql.query(query, epsilon=0.5, delta=1e-4)

    avg_age = res.map(lambda x: x.result.df["avg_age"][0])
    assert avg_age == IOSuccess(pytest.approx(51.5, 0.5))

    rem_budget = client.get_remaining_budget()
    assert rem_budget.map(lambda x: x.remaining_delta) == IOSuccess(pytest.approx(0.2, 1e-3))
    assert rem_budget.map(lambda x: x.remaining_epsilon) == IOSuccess(43.5)
    tot_spent = client.get_total_spent_budget()
    assert tot_spent.map(lambda x: x.total_spent_delta) == IOSuccess(pytest.approx(0, abs=1e-3))
    assert tot_spent.map(lambda x: x.total_spent_epsilon) == IOSuccess(1.5)

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 1
    assert prev_queries[0]["dataset_name"] == "TITANIC"
    assert prev_queries[0]["dp_library"] == "smartnoise_sql"


def test_demo_diffprivlib(kc, demo_setup: IOResultE) -> None:
    user_name = "Dr.Antartica"
    client = ClientIO(client_id=user_name, client_secret=user_name.lower(), dataset_name="PENGUIN")

    penguin_metadata_io = client.get_dataset_metadata()
    assert isinstance(penguin_metadata_io, IOSuccess)
    # Example of the Illegalest Function: IO t -> t ! (py)tests only !
    penguin_metadata = unsafe_perform_io(penguin_metadata_io.unwrap())
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

    dummy_response.map(lambda x: x.result.model) != IOSuccess(None)

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
    assert cost_res.map(lambda x: x.epsilon) == IOSuccess(pytest.approx(2, 0.1))
    assert cost_res.map(lambda x: x.delta) == IOSuccess(pytest.approx(0, abs=1e-4))

    predictions = flow(
        client.diffprivlib.query(
            pipeline=dpl_pipeline, feature_columns=feature_columns, target_columns=target_columns
        ),
        map_(
            lambda x: x.result.model.predict(
                pd.DataFrame(
                    {
                        "bill_length_mm": [bill_length_meta["lower"], bill_length_meta["upper"]],
                    }
                )
            )
        ),
    )

    assert predictions.map(len) == IOSuccess(2)
    assert predictions == IOSuccess(pytest.approx([20, 20], abs=20))

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
@pytest.mark.filterwarnings(
    "ignore:.*synthesizer random generator.*is not cryptographically secure:UserWarning"
)
def test_demo_smartnoise_synth(kc, demo_setup: IOResultE) -> None:
    user_name = "Dr.Antartica"
    client = ClientIO(client_id=user_name, client_secret=user_name.lower(), dataset_name="PENGUIN")

    cost_res = client.smartnoise_synth.cost(
        synth_name="aim",
        epsilon=1.0,
        delta=0.0001,
        select_cols=["species", "island"],
    )
    assert isinstance(cost_res, IOSuccess)
    assert cost_res.map(lambda x: x.epsilon) == IOSuccess(pytest.approx(1, 0.05))
    assert cost_res.map(lambda x: x.delta) == IOSuccess(pytest.approx(1e-4, abs=5e-5))

    for dummy in [True, False]:
        res_df = client.smartnoise_synth.query(
            synth_name="dpgan",
            epsilon=1.0,
            condition="body_mass_g > 5000",
            nb_samples=10,
            dummy=dummy,
        ).map(lambda x: x.result.df_samples)
        assert res_df.map(lambda df: df.flipper_length_mm.mean()) == IOSuccess(pytest.approx(200, 0.25))
        assert res_df.map(lambda df: df.body_mass_g.min() >= 5000) == IOSuccess(True)

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 1
    assert prev_queries[0]["dataset_name"] == "PENGUIN"
    assert prev_queries[0]["dp_library"] == "smartnoise_synth"
    response_archives = prev_queries[0]["response"]
    assert response_archives["epsilon"] == 1.0
    assert response_archives["delta"] >= 0.0


def test_demo_opendp_polars(kc, demo_setup: IOResultE) -> None:
    user_name = "Dr.FSO"
    client = ClientIO(
        client_id=user_name, client_secret=user_name.lower(), dataset_name="FSO_INCOME_SYNTHETIC"
    )
    income_metadata_io = client.get_dataset_metadata()
    assert isinstance(income_metadata_io, IOSuccess)

    NB_ROWS, SEED = 200, 0
    dummy_lf = client.get_dummy_dataset(nb_rows=NB_ROWS, seed=SEED, lazy=True)
    test = client.get_dummy_dataset(nb_rows=NB_ROWS, seed=SEED)
    assert map_(lambda x: len(x.dtypes) >= 5)(test) == IOSuccess(True)

    query_res = IOResultE.do(
        res
        for income_metadata in income_metadata_io
        for bounds in IOSuccess(
            (income_metadata["columns"]["income"]["lower"], income_metadata["columns"]["income"]["upper"])
        )
        for plan in dummy_lf.map(
            lambda df: df.select(pl.col("income").dp.mean(bounds=bounds, scale=(10_000, 1)))
        )
        for res in client.opendp.query(plan, dummy=False, nb_rows=NB_ROWS, seed=SEED)
    )
    assert query_res.map(lambda x: x.epsilon) == IOSuccess(pytest.approx(10, 2))
    assert query_res.map(lambda x: isinstance(x.result, OpenDPPolarsQueryResult)) == IOSuccess(True)
    assert query_res.map(lambda x: x.result.value.shape) == IOSuccess((1, 1))

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 1
    assert prev_queries[0]["dataset_name"] == "FSO_INCOME_SYNTHETIC"
    assert prev_queries[0]["dp_library"] == "opendp"
    assert prev_queries[0]["client_input"]["pipeline_type"] == "polars"
    assert prev_queries[0]["client_input"]["mechanism"] == "laplace"
    response_archives = prev_queries[0]["response"]
    assert response_archives["epsilon"] >= 1.0
    assert response_archives["delta"] >= 0.0

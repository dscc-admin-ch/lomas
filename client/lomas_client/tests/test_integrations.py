import io
import re
import sys
import time
from dataclasses import dataclass
from urllib.parse import urljoin

import numpy as np
import opendp.prelude as dp
import pandas as pd
import polars as pl
import pytest
import requests
from authlib.integrations.base_client.errors import OAuthError
from bs4 import BeautifulSoup
from diffprivlib import models
from opendp.mod import enable_features
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

enable_features("contrib")


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
    with pytest.raises(OAuthError, match=r"Invalid username or password"):
        aria.as_client()

    # Add a user
    add_dex_user(dex_config, aria.user_name, aria.user_email, aria.user_password)

    client = aria.as_client()

    with pytest.raises(UnauthorizedAccessException, match=f"User {aria.user_name} does not exist"):
        client.get_dataset_metadata()


class DeviceAuthorizationBot(io.StringIO):
    def __init__(self, user_name, user_password, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_name = user_name
        self.user_password = user_password
        self.found = False
        self.terminal = sys.stdout

    def verify_device(self, url):
        # url is something like http://localhost:4445/dex/device&user_code=ABDC-EFGH

        session = requests.Session()

        # 1. Access the verification page
        resp = session.get(url)
        resp.raise_for_status()

        # 2. Find the form and submit the user_code
        #    User code should already be filled out.
        soup = BeautifulSoup(resp.text, "html.parser")
        form_action = soup.find("form")["action"]
        # Handle relative paths
        form_action = urljoin(resp.url, form_action)
        user_code = soup.find("input", {"name": "user_code"})["value"]
        resp = session.post(form_action, data={"user_code": user_code})
        resp.raise_for_status()

        # 3. Handle the Login Page (Email/Password)
        soup = BeautifulSoup(resp.text, "html.parser")
        login_form = soup.find("form")
        login_url = urljoin(resp.url, login_form["action"])
        login_data = {"login": self.user_name, "password": self.user_password}

        resp = session.post(login_url, data=login_data)
        resp.raise_for_status()

        # 4. Approve
        soup = BeautifulSoup(resp.text, "html.parser")
        approve_form = soup.find("form")
        data = {}
        for hidden_input in approve_form.find_all("input", type="hidden"):
            data[hidden_input.get("name")] = hidden_input.get("value")

        resp = session.post(resp.url, data=data)
        resp.raise_for_status()

    def write(self, s):
        # Still print to console
        self.terminal.write(s)
        if not self.found:
            uri_match = re.search(r"http[s]?:[^\s]+", s)
            if uri_match:
                # Find verification url and authorize device
                self.found = True
                uri = uri_match.group(0)
                self.verify_device(uri)


@pytest.mark.long
@pytest.mark.timeout(15)
def test_device_flow(demo_setup) -> None:
    # Setup authorization bot
    user_name = "jack"
    bot = DeviceAuthorizationBot(
        user_name=f"{user_name}@example.com",
        user_password=user_name,
    )
    old_stdout = sys.stdout
    sys.stdout = bot

    client = Client(dataset_name="TITANIC", use_password_flow=False)

    # Reset stdout
    sys.stdout = old_stdout

    init_budget = client.get_initial_budget()
    assert init_budget.initial_delta == 0.2

    # Test refresh token works (our dex config sets lifetime of 10sec for access token)
    time.sleep(10)

    init_budget = client.get_initial_budget()
    assert init_budget.initial_delta == 0.2

    # Check new client uses saved token (in tempfile)
    client = Client(dataset_name="TITANIC", use_password_flow=False)

    init_budget = client.get_initial_budget()
    assert init_budget.initial_delta == 0.2


def test_oauth2_demo(dex_config, demo_setup) -> None:
    user_name = "Jack"
    client = Client(
        user_name=f"{user_name}@example.com", user_password=user_name.lower(), dataset_name="TITANIC"
    )

    init_budget = client.get_initial_budget()
    assert init_budget.initial_delta == 0.2
    assert init_budget.initial_epsilon == 45

    metadata = client.get_dataset_metadata()
    assert isinstance(metadata, dict)
    print("**************")
    print(metadata)

    df_dummy = client.get_dummy_dataset()
    assert df_dummy.shape == (100, 8)

    df_dummy_lz = client.get_dummy_dataset(lazy=True)
    assert df_dummy_lz.collect().shape == (100, 8)

    # Opendp #####################################

    # Prepare Query
    context = client.get_context(epsilon=DEFAULT_EPSILON)
    print("**************")
    print(context)
    plan = context.query().select(pl.col("Age").dp.mean(bounds=(0, 120)), dp.len())

    # Cost
    cost = client.opendp.cost(plan, epsilon=DEFAULT_EPSILON)
    assert cost.epsilon == 1.0

    cost_zcdp = client.opendp.cost(plan, rho=0.5, delta=1e-6)
    assert cost_zcdp.delta == 1e-6
    assert cost_zcdp.epsilon == pytest.approx(5, 0.5)

    # Dummy Query
    dummy_res = client.opendp.query(plan, dummy=True, epsilon=DEFAULT_EPSILON)
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
    res = client.opendp.query(plan, epsilon=DEFAULT_EPSILON)
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

    # Smartnoise #####################################

    # Dummy Query
    query = "SELECT COUNT(*) AS nb_passengers, AVG(Age) AS avg_age FROM df"
    dummy_res = client.smartnoise_sql.query(query=query, epsilon=100, delta=2, dummy=True)

    avg_age = dummy_res.result.df["avg_age"][0]
    assert avg_age == pytest.approx(51.5, 0.5)

    rem_budget = client.get_remaining_budget()
    assert rem_budget.remaining_delta == 0.2
    assert rem_budget.remaining_epsilon == 44
    tot_spent = client.get_total_spent_budget()
    assert tot_spent.total_spent_delta == 0
    assert tot_spent.total_spent_epsilon == 1.0

    # True Query
    res = client.smartnoise_sql.query(query, epsilon=0.5, delta=1e-4)

    avg_age = res.result.df["avg_age"][0]
    assert avg_age == pytest.approx(51.5, 0.5)

    rem_budget = client.get_remaining_budget()
    assert rem_budget.remaining_delta == pytest.approx(0.2, 1e-3)
    assert rem_budget.remaining_epsilon == 42.5
    tot_spent = client.get_total_spent_budget()
    assert tot_spent.total_spent_delta == pytest.approx(0, abs=1e-3)
    assert tot_spent.total_spent_epsilon == 2.5

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 2
    assert prev_queries[1]["dataset_name"] == "TITANIC"
    assert prev_queries[1]["dp_library"] == "smartnoise_sql"


def test_demo_diffprivlib(dex_config, demo_setup) -> None:
    user_name = "Dr.Antartica"
    client = Client(
        user_name=f"{user_name.lower()}@example.com", user_password=user_name.lower(), dataset_name="PENGUIN"
    )

    feature_columns = ["bill_length_mm", "bill_depth_mm", "flipper_length_mm", "body_mass_g"]
    target_columns = ["species"]
    bounds = ([30.0, 13.0, 150.0, 2000.0], [60.0, 23.0, 250.0, 2000.0])
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
    dpl_pipeline = Pipeline(
        [
            (
                "lr",
                models.LinearRegression(
                    epsilon=2.0,
                    bounds_X=(30.0, 65.0),
                    bounds_y=(13.0, 23.0),
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
                "bill_length_mm": [30.0, 65.0],
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
                "bill_length_mm": [30.0, 65.0],
            }
        )
    )

    assert len(predictions) == 2
    assert predictions == pytest.approx([20, 20], abs=20)


# @pytest.mark.long
# @pytest.mark.skip(reason="waiting on OpenDP 0.14 synth")
# def test_demo_smartnoise_synth(dex_config, demo_setup) -> None:
#     user_name = "Dr.Antartica"
#     client = Client(
#         user_name=f"{user_name.lower()}@example.com", user_password=user_name.lower(), dataset_name="PENGUIN"
#     )

#     cost_res = client.smartnoise_synth.cost(
#         synth_name="aim",
#         epsilon=1.0,
#         delta=0.0001,
#         select_cols=["species", "island"],
#     )
#     assert cost_res.epsilon == pytest.approx(1, 0.05)
#     assert cost_res.delta == pytest.approx(1e-4, abs=5e-5)

#     for dummy in [True, False]:
#         res = client.smartnoise_synth.query(
#             synth_name="dpgan",
#             epsilon=1.0,
#             condition="body_mass_g > 5000",
#             nb_samples=10,
#             dummy=dummy,
#         )
#         res_df = res.result.df_samples
#         assert res_df.flipper_length_mm.mean() == pytest.approx(200, 0.25)
#         assert res_df.body_mass_g.min() >= 5000

#     prev_queries = client.get_previous_queries()
#     assert len(prev_queries) == 1
#     assert prev_queries[0]["dataset_name"] == "PENGUIN"
#     assert prev_queries[0]["dp_library"] == "smartnoise_synth"
#     response_archives = prev_queries[0]["response"]
#     assert response_archives["epsilon"] == 1.0
#     assert response_archives["delta"] >= 0.0


def test_demo_opendp_polars(dex_config, demo_setup) -> None:
    user_name = "Dr.FSO"
    client = Client(
        user_name=f"{user_name.lower()}@example.com",
        user_password=user_name.lower(),
        dataset_name="FSO_INCOME_SYNTHETIC",
    )
    income_metadata = client.get_dataset_metadata()
    NB_ROWS, SEED = 200, 0
    context = client.get_context(epsilon=DEFAULT_EPSILON)
    test = client.get_dummy_dataset(nb_rows=NB_ROWS, seed=SEED)
    assert len(test.dtypes) >= 5

    columns = income_metadata["tableSchema"]["columns"]
    income_col = next(col for col in columns if col["name"] == "income")

    income_lower_bound = income_col["minimum"]
    income_upper_bound = income_col["maximum"]

    plan = context.query().select(pl.col("income").dp.mean(bounds=(income_lower_bound, income_upper_bound)))
    query_res = client.opendp.query(plan, nb_rows=NB_ROWS, seed=SEED, epsilon=DEFAULT_EPSILON)
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

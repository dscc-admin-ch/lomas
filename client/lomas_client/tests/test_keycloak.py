from dataclasses import dataclass

import pytest
from mantelo import KeycloakAdmin
from oauthlib import oauth2

from lomas_client import Client
from lomas_core.error_handler import UnauthorizedAccessException
from lomas_core.models.config import AdminConfig, KeycloakClientConfig
from lomas_server.administration.keycloak_admin import (
    add_kc_user,
    del_all_kc_users,
    get_kc_admin,
)
from lomas_server.administration.scripts.lomas_demo_setup import lomas_demo_setup


@pytest.fixture
def demo_setup():
    lomas_demo_setup()


@dataclass
class Aria:
    user_name: str = "aria"
    user_email: str = "aria.stark@winterfell.no"
    client_secret: str = "secret_aria"

    def as_client(self, dataset_name="anyName") -> Client:
        return Client(client_id=self.user_name, client_secret=self.client_secret, dataset_name=dataset_name)


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
        Client()


def test_oauth2(aria, kc) -> None:
    with pytest.raises(oauth2.InvalidClientError, match=r"Invalid client credentials"):
        aria.as_client()

    # Add a user
    add_kc_user(kc.config, aria.user_name, aria.user_email, aria.client_secret)

    client = aria.as_client()

    with pytest.raises(UnauthorizedAccessException, match=f"User {aria.user_name} does not exist"):
        client.get_dataset_metadata()


def test_oauth2_demo(kc, demo_setup) -> None:
    client = Client(client_id="Jack", client_secret="jack", dataset_name="TITANIC")

    init_budget = client.get_initial_budget()
    assert init_budget.initial_delta == 0.2
    assert init_budget.initial_epsilon == 45

    assert set(client.get_dataset_metadata().keys()) == {
        "censor_dims",
        "columns",
        "max_ids",
        "rows",
        "row_privacy",
    }

    df_dummy = client.get_dummy_dataset()
    assert df_dummy.shape == (100, 11)

    df_dummy_lz = client.get_dummy_dataset(lazy=True)
    assert df_dummy_lz.collect().shape == (100, 11)

    # Dummy Query
    query = "SELECT COUNT(*) AS nb_passengers, AVG(Age) AS avg_age FROM df"
    dummy_res = client.smartnoise_sql.query(query=query, epsilon=100, delta=2, dummy=True)

    avg_age = dummy_res.result.df["avg_age"][0]
    assert avg_age == pytest.approx(51.5, 0.5)

    rem_budget = client.get_remaining_budget()
    assert rem_budget.remaining_delta == 0.2
    assert rem_budget.remaining_epsilon == 45
    tot_spent = client.get_total_spent_budget()
    assert tot_spent.total_spent_delta == 0
    assert tot_spent.total_spent_epsilon == 0

    # True Query
    res = client.smartnoise_sql.query(query, epsilon=0.5, delta=1e-4)

    avg_age = res.result.df["avg_age"][0]
    assert avg_age == pytest.approx(51.5, 0.5)

    rem_budget = client.get_remaining_budget()
    assert rem_budget.remaining_delta == pytest.approx(0.2, 1e-3)
    assert rem_budget.remaining_epsilon == 43.5
    tot_spent = client.get_total_spent_budget()
    assert tot_spent.total_spent_delta == pytest.approx(0, abs=1e-3)
    assert tot_spent.total_spent_epsilon == 1.5

    prev_queries = client.get_previous_queries()
    assert len(prev_queries) == 1
    assert prev_queries[0]["dataset_name"] == "TITANIC"

import json

from fastapi import status
from fastapi.testclient import TestClient
from lomas_core.models.responses import (
    CostResponse,
    QueryResponse,
    SmartnoiseSynthModel,
    SmartnoiseSynthSamples,
)
from smartnoise_synth_logger import serialise_constraints
from snsynth.transform import (
    ChainTransformer,
    LabelTransformer,
    MinMaxTransformer,
    OneHotEncoder,
)

from lomas_server.app import app
from lomas_server.tests.constants import PENGUIN_COLUMNS, PUMS_COLUMNS
from lomas_server.tests.test_api import TestRootAPIEndpoint
from lomas_server.utils.query_examples import (
    example_dummy_smartnoise_synth_query,
    example_smartnoise_synth_cost,
    example_smartnoise_synth_query,
)


def validate_response(response) -> QueryResponse:
    """Validate that the pipeline ran successfully.

    Returns a model and a score.
    """
    assert response.status_code == status.HTTP_200_OK
    response_dict = json.loads(response.content.decode("utf8"))

    r_model = QueryResponse.model_validate(response_dict)
    assert isinstance(r_model.result, SmartnoiseSynthModel | SmartnoiseSynthSamples)

    return r_model


class TestSmartnoiseSynthEndpoint(TestRootAPIEndpoint):  # pylint: disable=R0904
    """Test Smartnoise Synth Endpoints with different Synthesizers."""

    def test_smartnoise_synth_query(self) -> None:
        """Test smartnoise synth query."""
        with TestClient(app, headers=self.headers) as client:
            # Expect to work
            response = client.post(
                "/smartnoise_synth_query",
                json=example_smartnoise_synth_query,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            r_model = validate_response(response)

            assert r_model.requested_by == self.user_name
            assert r_model.epsilon >= 0.1
            assert r_model.delta >= 1e-05

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            assert model.__class__.__name__ == "DPCTGAN"

            df = model.sample(10)
            assert list(df.columns) == PENGUIN_COLUMNS

            # Expect to fail due to parameters
            body = dict(example_smartnoise_synth_query)
            body["synth_params"] = {}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert response.json() == {
                "ExternalLibraryException": "Error fitting model: "
                + "sample_rate=1.4534883720930232 is not a valid value. "
                + "Please provide a float between 0 and 1. "
                + "Try decreasing batch_size in "
                + "synth_params (default batch_size=500).",
                "library": "smartnoise_synth",
            }

    def test_smartnoise_synth_query_samples(self) -> None:
        """Test smartnoise synth query return samples."""
        with TestClient(app, headers=self.headers) as client:
            nb_samples = 100

            body = dict(example_smartnoise_synth_query)
            body["return_model"] = False
            body["nb_samples"] = nb_samples

            # Expect to work - no condition
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthSamples)
            df_0 = r_model.result.df_samples
            assert df_0.shape[0] == nb_samples
            assert list(df_0.columns) == PENGUIN_COLUMNS

            # Expect to work - condition
            body["condition"] = "bill_length_mm < 40"
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthSamples)
            df_1 = r_model.result.df_samples
            assert df_1.shape[0] == nb_samples
            assert list(df_1.columns) == PENGUIN_COLUMNS

            assert df_0["bill_length_mm"].mean() > df_1["bill_length_mm"].mean()

    def test_smartnoise_synth_query_select_cols(self) -> None:
        """Test smartnoise synth query select_cols."""
        with TestClient(app, headers=self.headers) as client:

            # Expect to work
            body = dict(example_smartnoise_synth_query)
            body["select_cols"] = ["species", "island"]
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == ["species", "island"]

            # Expect to fail
            body = dict(example_smartnoise_synth_query)
            body["select_cols"] = ["species", "idonotexist"]
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json()["InvalidQueryException"].startswith(
                "Error while selecting provided select_cols: "
            )

    def test_smartnoise_synth_query_constraints(self) -> None:
        """Test smartnoise synth query constraints."""
        with TestClient(app, headers=self.headers) as client:

            constraints = {
                "species": ChainTransformer(
                    [LabelTransformer(nullable=True), OneHotEncoder()]
                ),
                "island": ChainTransformer(
                    [LabelTransformer(nullable=True), OneHotEncoder()]
                ),
                "bill_length_mm": MinMaxTransformer(
                    lower=30.0, upper=65.0, nullable=True
                ),
                "bill_depth_mm": MinMaxTransformer(
                    lower=13.0, upper=23.0, nullable=True
                ),
                "flipper_length_mm": MinMaxTransformer(
                    lower=150.0, upper=250.0, nullable=True
                ),
                "body_mass_g": MinMaxTransformer(
                    lower=2000.0, upper=7000.0, nullable=True
                ),
                "sex": ChainTransformer(
                    [LabelTransformer(nullable=True), OneHotEncoder()]
                ),
            }

            body = dict(example_smartnoise_synth_query)
            body["constraints"] = serialise_constraints(constraints)

            # Expect to work
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == PENGUIN_COLUMNS

    def test_smartnoise_synth_query_private_id(self) -> None:
        """Test smartnoise synth query on other dataset for private id.

        and categorical int columns
        """
        with TestClient(app, headers=self.headers) as client:

            # Expect to work
            body = dict(example_smartnoise_synth_query)
            body["dataset_name"] = "PUMS"
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == PUMS_COLUMNS

    def test_smartnoise_synth_query_delta_none(self) -> None:
        """Test smartnoise synth query on other synthesizer with delta None."""
        with TestClient(app, headers=self.headers) as client:

            # Expect to work
            body = dict(example_dummy_smartnoise_synth_query)
            body["dataset_name"] = "PUMS"
            body["delta"] = None
            body["synth_params"] = {"batch_size": 2, "epochs": 5}
            response = client.post(
                "/dummy_smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == PUMS_COLUMNS

    def test_dummy_smartnoise_synth_query(self) -> None:
        """Test_dummy_smartnoise_synth_query."""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/dummy_smartnoise_synth_query",
                json=example_dummy_smartnoise_synth_query,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            assert model.__class__.__name__ == "DPCTGAN"

            # Expect to fail: user does have access to dataset
            body = dict(example_dummy_smartnoise_synth_query)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/dummy_smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }

    def test_smartnoise_synth_cost(self) -> None:
        """Test_smartnoise_synth_cost."""
        with TestClient(app) as client:
            # Expect to work
            response = client.post(
                "/estimate_smartnoise_synth_cost",
                json=example_smartnoise_synth_cost,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_200_OK

            response_dict = json.loads(response.content.decode("utf8"))
            r_model = CostResponse.model_validate(response_dict)
            assert r_model.epsilon >= 0.1
            assert r_model.delta >= 1e-5

            # Expect to fail: user does have access to dataset
            body = dict(example_smartnoise_synth_cost)
            body["dataset_name"] = "IRIS"
            response = client.post(
                "/estimate_smartnoise_synth_cost",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert response.json() == {
                "UnauthorizedAccessException": ""
                + f"{self.user_name} does not have access to IRIS."
            }

    def test_smartnoise_synth_query_datetime(self) -> None:
        """Test smartnoise synth query on other dataset for datetime columns."""
        with TestClient(app) as client:

            # Expect to work
            new_headers = self.headers
            new_headers["user-name"] = "BirthdayGirl"

            body = dict(example_smartnoise_synth_query)
            body["dataset_name"] = "BIRTHDAYS"
            body["synth_params"]["batch_size"] = 2  # type: ignore
            # With gan synthesizer
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=new_headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == new_headers["user-name"]

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == ["birthday"]

            # With marginal synthesizer
            body["synth_name"] = "mwem"
            body["delta"] = None
            body["synth_params"] = {}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=new_headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == new_headers["user-name"]

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == ["birthday"]

    def test_smartnoise_synth_query_aim(self) -> None:
        """Test smartnoise synth query AIM Synthesizer."""
        with TestClient(app) as client:
            # Expect to work
            body = dict(example_smartnoise_synth_query)
            body["synth_name"] = "aim"
            body["select_cols"] = [
                "bill_depth_mm",
                "species",
            ]  # too slow otherwise
            body["synth_params"] = {}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == body["select_cols"]

    def test_smartnoise_synth_query_mwem(self) -> None:
        """Test smartnoise synth query MWEM Synthesizer."""
        with TestClient(app) as client:

            # Expect to fail: delta
            body = dict(example_smartnoise_synth_query)
            body["synth_name"] = "mwem"
            body["synth_params"] = {}
            body["select_cols"] = ["species", "island"]
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert response.json() == {
                "ExternalLibraryException": "Error creating model: "
                + "MWEMSynthesizer.__init__() got an "
                + "unexpected keyword argument 'delta'",
                "library": "smartnoise_synth",
            }

            # Expect to work: limited columns and delta None
            body["delta"] = None
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == ["species", "island"]

            # Expect to work: special parameters
            body["synth_params"] = {"split_factor": 2, "measure_only": False}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == ["species", "island"]

    def test_smartnoise_synth_query_mst(self) -> None:
        """Test smartnoise synth query MST Synthesizer."""
        with TestClient(app) as client:

            # Expect to work:
            body = dict(example_smartnoise_synth_query)
            body["synth_name"] = "mst"
            body["return_model"] = False
            body["nb_samples"] = 10
            body["select_cols"] = ["bill_length_mm"]  # too slow otherwise
            body["synth_params"] = {}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )

            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthSamples)
            df = r_model.result.df_samples
            assert df.shape[0] == body["nb_samples"]
            assert list(df.columns) == body["select_cols"]

            # Espect to fail: MST cannot return model
            body["return_model"] = True
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json()["InvalidQueryException"].startswith(
                "mst synthesizer cannot be returned, only samples. "
                + "Please, change model or set `return_model=False`"
            )

    def test_smartnoise_synth_query_pacsynth(self) -> None:
        """Test smartnoise synth query PAC-Synth Synthesizer.

        TOO UNSTABLE BECAUSE OF RUST PANIC
        """
        with TestClient(app) as client:
            # Expect to fail:  #TODO why
            body = dict(example_smartnoise_synth_query)
            body["synth_name"] = "pacsynth"
            body["synth_params"] = {}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json()["InvalidQueryException"].startswith(
                "pacsynth synthesizer not supported due to Rust panic. "
                + "Please select another Synthesizer."
            )

    def test_smartnoise_synth_query_patectgan(self) -> None:
        """Test smartnoise synth query PATE-CTGAN Synthesizer."""
        with TestClient(app) as client:

            # Expect to fail: epsilon too small
            body = dict(example_smartnoise_synth_query)
            body["synth_name"] = "patectgan"
            body["synth_params"] = {}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert response.json() == {
                "ExternalLibraryException": "Error fitting model: "
                + "Inputted epsilon parameter is too small to create a private"
                + " dataset. Try increasing epsilon and rerunning.",
                "library": "smartnoise_synth",
            }

            # Expect to work
            body["epsilon"] = 1.0
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == PENGUIN_COLUMNS

    def test_smartnoise_synth_query_pategan(self) -> None:
        """Test smartnoise synth query pategan Synthesizer."""
        with TestClient(app) as client:

            # Expect to fail: penguin dataset is too small
            # (pategan needs > 1000 rows)
            body = dict(example_smartnoise_synth_query)
            body["synth_name"] = "pategan"
            body["synth_params"] = {}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert response.json() == {
                "ExternalLibraryException": "pategan not reliable with this dataset.",
                "library": "smartnoise_synth",
            }

    def test_smartnoise_synth_query_dpgan(self) -> None:
        """Test smartnoise synth query dpgan Synthesizer."""
        with TestClient(app) as client:

            # Expect to fail: epsilon too small
            body = dict(example_smartnoise_synth_query)
            body["synth_name"] = "dpgan"
            body["synth_params"] = {}
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            assert response.json() == {
                "ExternalLibraryException": "Error fitting model: "
                + "Inputted epsilon and sigma parameters "
                + "are too small to create a private dataset. "
                + "Try increasing either parameter and rerunning.",
                "library": "smartnoise_synth",
            }

            body["epsilon"] = 1.0
            response = client.post(
                "/smartnoise_synth_query",
                json=body,
                headers=self.headers,
            )
            r_model = validate_response(response)
            assert r_model.requested_by == self.user_name

            assert isinstance(r_model.result, SmartnoiseSynthModel)
            model = r_model.result.model
            df = model.sample(1)
            assert list(df.columns) == PENGUIN_COLUMNS

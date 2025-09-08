import base64
import json
import pickle
from functools import wraps

import pandas as pd
import polars as pl
from opendp.mod import enable_features
from opendp_logger import enable_logging
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pydantic import ValidationError
from returns.io import IOResultE
from returns.pipeline import flow
from returns.pointfree import bind, map_
from returns.unsafe import unsafe_perform_io

from lomas_client.constants import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
)
from lomas_client.http_client import LomasHttpClient
from lomas_client.libraries.diffprivlib import DiffPrivLibClient
from lomas_client.libraries.opendp import OpenDPClient
from lomas_client.libraries.smartnoise_sql import SmartnoiseSQLClient
from lomas_client.libraries.smartnoise_synth import SmartnoiseSynthClient
from lomas_client.models.config import ClientConfig
from lomas_client.utils import parse_if_ok
from lomas_core.constants import DPLibraries
from lomas_core.instrumentation import init_telemetry
from lomas_core.models.requests import GetDummyDataset, LomasRequestModel, OpenDPQueryModel
from lomas_core.models.responses import (
    DummyDsResponse,
    InitialBudgetResponse,
    RemainingBudgetResponse,
    SpentBudgetResponse,
)
from lomas_core.opendp_utils import reconstruct_measurement_pipeline

# Opendp_logger
enable_logging()
enable_features("contrib")


class ClientIO:
    """Client class to send requests to the server.

    Handle all serialisation and deserialisation steps
    """

    def __init__(self, **kwargs: ClientConfig.model_config):
        """Initializes the Client with the specified URL, dataset name and authentication parameters.

        Args:
            kwargs: All keyword arguments will be forwarded to the ClientConfig
        """

        try:
            self.config = ClientConfig(**kwargs)
        except ValidationError as exc:
            raise ValueError(
                "Missing one of or invalid: client_id, client_secret, keycloak_url"
                "or realm when using jwt authentication method."
                "If you are using this library from a managed environment and don't know "
                "about your credentials, please contact your system administrator."
            ) from exc

        if self.config.telemetry.enabled:
            LoggingInstrumentor().instrument(set_logging_format=True)
            init_telemetry(self.config.telemetry)

        self.http_client = LomasHttpClient(self.config)
        self.smartnoise_sql = SmartnoiseSQLClient(self.http_client)
        self.smartnoise_synth = SmartnoiseSynthClient(self.http_client)
        self.opendp = OpenDPClient(self.http_client)
        self.diffprivlib = DiffPrivLibClient(self.http_client)

    def get_dataset_metadata(self) -> IOResultE[LomasRequestModel]:
        """This function retrieves metadata for the dataset.

        Returns:
            LomasRequestModel:
                A dictionary containing dataset metadata.
        """

        return flow(
            # construct request body
            {"dataset_name": self.config.dataset_name},
            # validate request model
            LomasRequestModel.model_validate,
            # post to the validated body to the corresponding endpoint
            lambda body: self.http_client.post("get_dataset_metadata", body),
            # parse reply if HTTP 200
            bind(parse_if_ok),
            # load successful response as json
            map_(json.loads),
        )

    def get_dummy_dataset(
        self,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
        lazy: bool = False,
    ) -> IOResultE[pd.DataFrame | pl.LazyFrame]:
        """This function retrieves a dummy dataset with optional parameters.

        Args:
            nb_rows (int, optional): The number of rows in the dummy dataset.
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.
                Defaults to DUMMY_SEED.
            lazy (bool, optional): If True, return a polars LazyFrame.
                Defaults to False (pandas DataFrame)

        Returns:
            pd.DataFrame | pl.LazyFrame: A Pandas DataFrame representing
            the dummy dataset (optionally in LazyFrame format).
        """
        return flow(
            # construct request body
            {
                "dataset_name": self.config.dataset_name,
                "dummy_nb_rows": nb_rows,
                "dummy_seed": seed,
            },
            # validate request model
            GetDummyDataset.model_validate,
            # post to the validated body to the corresponding endpoint
            lambda body: self.http_client.post("get_dummy_dataset", body),
            # parse reply if HTTP 200
            bind(parse_if_ok),
            # load successful response as json
            map_(DummyDsResponse.model_validate_json),
            map_(
                lambda dummy_ds_res: (
                    pl.from_pandas(dummy_ds_res.dummy_df).lazy() if lazy else dummy_ds_res.dummy_df
                )
            ),
        )

    def get_dummy_lf(self, nb_rows: int = DUMMY_NB_ROWS, seed: int = DUMMY_SEED) -> pl.LazyFrame:
        """
        Returns the polars LazyFrame for the dummy dataset with optional parameters.

        Args:
            nb_rows (int, optional): The number of rows in the dummy dataset.
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.
                Defaults to DUMMY_SEED.

        Returns:
            Optional[pl.LazyFrame]: The LazyFrame for the dummy dataset
        """
        dummy_pandas = self.get_dummy_dataset(nb_rows=nb_rows, seed=seed)

        # TODO: fix when pandas can handle datetime
        for col in dummy_pandas.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
            dummy_pandas[col] = dummy_pandas[col].astype(str)
        return pl.from_pandas(dummy_pandas).lazy()

    def get_initial_budget(self) -> IOResultE[InitialBudgetResponse]:
        """This function retrieves the initial budget.

        Returns:
            InitialBudgetResponse: A dictionary
                containing the initial budget.
        """

        return flow(
            # construct request body
            {"dataset_name": self.config.dataset_name},
            # validate request model
            LomasRequestModel.model_validate,
            # post to the validated body to the corresponding endpoint
            lambda body: self.http_client.post("get_initial_budget", body),
            # parse reply if HTTP 200
            bind(parse_if_ok),
            # build Budget Response from successful json payload
            map_(InitialBudgetResponse.model_validate_json),
        )

    def get_total_spent_budget(self) -> IOResultE[SpentBudgetResponse]:
        """This function retrieves the total spent budget.

        Returns:
            SpentBudgetResponse: A dictionary containing
                the total spent budget.
        """
        return flow(
            # construct request body
            {"dataset_name": self.config.dataset_name},
            # validate request model
            LomasRequestModel.model_validate,
            # post to the validated body to the corresponding endpoint
            lambda body: self.http_client.post("get_total_spent_budget", body),
            # parse reply if HTTP 200
            bind(parse_if_ok),
            # build Budget Response from successful json payload
            map_(SpentBudgetResponse.model_validate_json),
        )

    def get_remaining_budget(self) -> IOResultE[RemainingBudgetResponse]:
        """This function retrieves the remaining budget.

        Returns:
            RemainingBudgetResponse: A dictionary
                containing the remaining budget.
        """
        return flow(
            # construct request body
            {"dataset_name": self.config.dataset_name},
            # validate request model
            LomasRequestModel.model_validate,
            # post to the validated body to the corresponding endpoint
            lambda body: self.http_client.post("get_remaining_budget", body),
            # parse reply if HTTP 200
            bind(parse_if_ok),
            # build Budget Response from successful json payload
            map_(RemainingBudgetResponse.model_validate_json),
        )

    def get_previous_queries(self) -> IOResultE[list[dict]]:
        """This function retrieves the previous queries of the user.

        Raises:
            ValueError: If an unknown query type is encountered
                during deserialization.

        Returns:
            List[dict]: A list of dictionary containing
            the different queries on the private dataset.
        """

        def post_processes_queries(queries: list[dict]) -> list[dict]:
            deserialised_queries = []
            for query in queries:
                match query["dp_library"]:
                    case DPLibraries.SMARTNOISE_SQL:
                        pass
                    case DPLibraries.SMARTNOISE_SYNTH:
                        return_model = query["client_input"]["return_model"]
                        res = query["response"]["result"]
                        if return_model:
                            query["response"]["result"] = pickle.loads(base64.b64decode(res))
                        else:
                            query["response"]["result"] = pd.DataFrame(res)
                    case DPLibraries.OPENDP:
                        query_json = OpenDPQueryModel.model_validate(query["client_input"])
                        query["client_input"]["opendp_json"] = reconstruct_measurement_pipeline(
                            query_json, self.get_dataset_metadata()
                        )
                    case DPLibraries.DIFFPRIVLIB:
                        model = base64.b64decode(query["response"]["result"]["model"])
                        query["response"]["result"]["model"] = pickle.loads(model)
                    case _:
                        raise ValueError(f"Cannot deserialise unknown query type: {query['dp_library']}")

                deserialised_queries.append(query)

            return deserialised_queries

        return flow(
            # construct request body
            {"dataset_name": self.config.dataset_name},
            # validate request model
            LomasRequestModel.model_validate,
            # post to the validated body to the corresponding endpoint
            lambda body: self.http_client.post("get_previous_queries", body),
            # parse reply if HTTP 200
            bind(parse_if_ok),
            bind(lambda content: json.loads(content)["previous_queries"]),
            post_processes_queries,
        )


# FIXME: how to cleanly shadow Client without to much python __darkmagic__ ...


def call_and_unwrap_wrapper(method):
    @wraps(method)
    def call_and_unwrap(*args, **kwargs):
        result = method(*args, **kwargs)
        if hasattr(result, "unwrap"):
            return unsafe_perform_io(result.unwrap())
        return result

    return call_and_unwrap


class SmartnoiseSQLClientU(SmartnoiseSQLClient):
    def __getattribute__(self, name, *args):
        attr = super().__getattribute__(name)
        if callable(attr):
            return call_and_unwrap_wrapper(attr)
        return attr


class OpenDPClientU(OpenDPClient):
    def __getattribute__(self, name, *args):
        attr = super().__getattribute__(name)
        if callable(attr):
            return call_and_unwrap_wrapper(attr)
        return attr


class SmartnoiseSynthClientU(SmartnoiseSynthClient):
    def __getattribute__(self, name, *args):
        attr = super().__getattribute__(name)
        if callable(attr):
            return call_and_unwrap_wrapper(attr)
        return attr


class DiffPrivLibClientU(DiffPrivLibClient):
    def __getattribute__(self, name, *args):
        attr = super().__getattribute__(name)
        if callable(attr):
            return call_and_unwrap_wrapper(attr)
        return attr


class Client(ClientIO):
    def __getattribute__(self, name, *args):
        attr = super().__getattribute__(name)
        if callable(attr):
            return call_and_unwrap_wrapper(attr)
        return attr

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.smartnoise_sql = SmartnoiseSQLClientU(self.http_client)
        self.smartnoise_synth = SmartnoiseSynthClientU(self.http_client)
        self.opendp = OpenDPClientU(self.http_client)
        self.diffprivlib = DiffPrivLibClientU(self.http_client)

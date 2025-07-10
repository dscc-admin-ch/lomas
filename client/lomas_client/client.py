import base64
import json
import pickle

import pandas as pd
import polars as pl
from fastapi import status
from opendp.mod import enable_features
from opendp_logger import enable_logging, make_load_json
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from pydantic import ValidationError

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
from lomas_client.utils import raise_error, validate_model_response_direct
from lomas_core.constants import DPLibraries
from lomas_core.instrumentation import init_telemetry
from lomas_core.models.requests import (
    GetDummyDataset,
    LomasRequestModel,
)
from lomas_core.models.responses import (
    DummyDsResponse,
    InitialBudgetResponse,
    RemainingBudgetResponse,
    SpentBudgetResponse,
)

# Opendp_logger
enable_logging()
enable_features("contrib")


class Client:
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

    def get_dataset_metadata(self) -> LomasRequestModel:
        """This function retrieves metadata for the dataset.

        Returns:
            LomasRequestModel:
                A dictionary containing dataset metadata.
        """
        body_dict = {"dataset_name": self.config.dataset_name}
        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_dataset_metadata", body)
        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            metadata = json.loads(data)
            return metadata

        raise_error(res)

    def get_dummy_dataset(
        self,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
        lazy: bool = False,
    ) -> pd.DataFrame | pl.LazyFrame:
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
        body_dict = {
            "dataset_name": self.config.dataset_name,
            "dummy_nb_rows": nb_rows,
            "dummy_seed": seed,
        }
        body = GetDummyDataset.model_validate(body_dict)
        res = self.http_client.post("get_dummy_dataset", body)

        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            validated_response = DummyDsResponse.model_validate_json(data)
            dummy_df = validated_response.dummy_df
            if lazy:
                # Temporary: we use type string for datetime in polars
                # Will be fixed in 0.13
                for col in dummy_df.select_dtypes(include=["datetime"]):
                    dummy_df[col] = dummy_df[col].astype("string[python]")
                print(
                    "Datetime type mismatch: The Polars LazyFrame currently uses 'str' for datetime fields, "
                    "which may not match the expected metadata types. This is a temporary workaround "
                    "and will be resolved in a future release (>=0.13)."
                )
                return pl.from_pandas(dummy_df).lazy()

            for col in validated_response.int_with_nulls_columns:
                dummy_df[col] = (
                    dummy_df[col].where(~pd.isna(dummy_df[col]), other=pd.NA).round().astype("Int64")
                )
            return dummy_df

        raise_error(res)

    def get_dummy_lf(self, nb_rows: int = DUMMY_NB_ROWS, seed: int = DUMMY_SEED) -> pl.LazyFrame:
        """
        Returns the polars LazyFrame for the dummy dataset with.

        optional parameters.
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

    def get_initial_budget(self) -> InitialBudgetResponse:
        """This function retrieves the initial budget.

        Returns:
            InitialBudgetResponse: A dictionary
                containing the initial budget.
        """

        body_dict = {"dataset_name": self.config.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_initial_budget", body)

        return validate_model_response_direct(res, InitialBudgetResponse)

    def get_total_spent_budget(self) -> SpentBudgetResponse:
        """This function retrieves the total spent budget.

        Returns:
            SpentBudgetResponse: A dictionary containing
                the total spent budget.
        """
        body_dict = {"dataset_name": self.config.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_total_spent_budget", body)

        return validate_model_response_direct(res, SpentBudgetResponse)

    def get_remaining_budget(self) -> RemainingBudgetResponse:
        """This function retrieves the remaining budget.

        Returns:
            RemainingBudgetResponse: A dictionary
                containing the remaining budget.
        """
        body_dict = {"dataset_name": self.config.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_remaining_budget", body)

        return validate_model_response_direct(res, RemainingBudgetResponse)

    def get_previous_queries(self) -> list[dict]:
        """This function retrieves the previous queries of the user.

        Raises:
            ValueError: If an unknown query type is encountered
                during deserialization.

        Returns:
            List[dict]: A list of dictionary containing
            the different queries on the private dataset.
        """
        body_dict = {"dataset_name": self.config.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_previous_queries", body)

        if res.status_code == status.HTTP_200_OK:
            queries = json.loads(res.content.decode("utf8"))["previous_queries"]

            if not queries:
                return queries

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
                        opdp_query = make_load_json(query["client_input"]["opendp_json"])
                        query["client_input"]["opendp_json"] = opdp_query
                    case DPLibraries.DIFFPRIVLIB:
                        model = base64.b64decode(query["response"]["result"]["model"])
                        query["response"]["result"]["model"] = pickle.loads(model)
                    case _:
                        raise ValueError(f"Cannot deserialise unknown query type: {query['dp_library']}")

                deserialised_queries.append(query)

            return deserialised_queries

        raise_error(res)

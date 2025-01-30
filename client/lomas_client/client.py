import base64
import json
import pickle
from typing import List, Optional

import pandas as pd
import polars as pl
from fastapi import status
from opendp.mod import enable_features
from opendp_logger import enable_logging, make_load_json

from lomas_client.constants import (
    CLIENT_SERVICE_NAME,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    SERVICE_ID,
)
from lomas_client.http_client import LomasHttpClient
from lomas_client.libraries.diffprivlib import DiffPrivLibClient
from lomas_client.libraries.opendp import OpenDPClient
from lomas_client.libraries.smartnoise_sql import SmartnoiseSQLClient
from lomas_client.libraries.smartnoise_synth import SmartnoiseSynthClient
from lomas_client.utils import raise_error, validate_model_response_direct
from lomas_core.constants import DPLibraries
from lomas_core.instrumentation import get_ressource, init_telemetry
from lomas_core.models.constants import AuthenticationType
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

    def __init__(
        self,
        url: str,
        dataset_name: str,
        auth_method: AuthenticationType = AuthenticationType.JWT,
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        keycloak_address: Optional[str] = None,
        keycloak_port: Optional[int] = None,
        realm: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        """Initializes the Client with the specified URL, dataset name and authentication parameters.

        Args:
            url (str): The base URL for the API server.
            dataset_name (str): The name of the dataset to be accessed or manipulated.
            auth_method (AuthenticationType, optional): The authentication method to use
                with the lomas server, one of AuthenticationType. Defaults to AuthenticationType.JWT.
            user_name (str, optional): The name of the user allowed to perform queries, if using
                free pass authentication. Defaults to None.
            user_email (str, optional): The email of the user, if using free passauthentication.
                Defaults to None.
            keycloak_address (str, optional): Overwrites the keycloak address (otherwise passed by
                environment variable), if using jwt authentication. Defaults to None.
            keycloak_port (str, optional): Overwrites the keycloak port (otherwise passed by
                environment variable), if using jwt authentication. Defaults to None.
            realm (str, optional): Overwrites the realm (otherwise passed by environment variable),
                if using jwt authentication. Defaults to None.
            client_id (str, optional): Overwrites the client id of the user's associated service account
                (otherwise passed by environment variable), if using jwt authentication. Defaults to None.
            client_secret (str, optional): Overwrites the client id of the user's associated service account
                (otherwise passed by environment variable), if using jwt authentication. Defaults to None.
        """

        resource = get_ressource(CLIENT_SERVICE_NAME, SERVICE_ID)
        init_telemetry(resource)

        self.http_client = LomasHttpClient(
            url,
            dataset_name,
            auth_method,
            user_name,
            user_email,
            keycloak_address,
            keycloak_port,
            realm,
            client_id,
            client_secret,
        )
        self.smartnoise_sql = SmartnoiseSQLClient(self.http_client)
        self.smartnoise_synth = SmartnoiseSynthClient(self.http_client)
        self.opendp = OpenDPClient(self.http_client)
        self.diffprivlib = DiffPrivLibClient(self.http_client)

    def get_dataset_metadata(
        self,
    ) -> Optional[LomasRequestModel]:
        """This function retrieves metadata for the dataset.

        Returns:
            Optional[LomasRequestModel]:
                A dictionary containing dataset metadata.
        """
        body_dict = {"dataset_name": self.http_client.dataset_name}
        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_dataset_metadata", body)
        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            metadata = json.loads(data)
            return metadata

        raise_error(res)
        return None

    def get_dummy_dataset(
        self,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[DummyDsResponse]:
        """This function retrieves a dummy dataset with optional parameters.

        Args:
            nb_rows (int, optional): The number of rows in the dummy dataset.

                Defaults to DUMMY_NB_ROWS.

            seed (int, optional): The random seed for generating the dummy dataset.

                Defaults to DUMMY_SEED.

        Returns:
            Optional[DummyDsResponse]: A Pandas DataFrame
                representing the dummy dataset.
        """
        body_dict = {
            "dataset_name": self.http_client.dataset_name,
            "dummy_nb_rows": nb_rows,
            "dummy_seed": seed,
        }
        body = GetDummyDataset.model_validate(body_dict)
        res = self.http_client.post("get_dummy_dataset", body)

        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            res_model = DummyDsResponse.model_validate_json(data)
            return res_model.dummy_df

        raise_error(res)
        return None

    def get_dummy_lf(self, nb_rows: int = DUMMY_NB_ROWS, seed: int = DUMMY_SEED) -> Optional[pl.LazyFrame]:
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

        if dummy_pandas is None:
            return None
        return pl.from_pandas(dummy_pandas).lazy()

    def get_initial_budget(self) -> Optional[InitialBudgetResponse]:
        """This function retrieves the initial budget.

        Returns:
            Optional[InitialBudgetResponse]: A dictionary
                containing the initial budget.
        """

        body_dict = {"dataset_name": self.http_client.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_initial_budget", body)

        return validate_model_response_direct(res, InitialBudgetResponse)

    def get_total_spent_budget(self) -> Optional[SpentBudgetResponse]:
        """This function retrieves the total spent budget.

        Returns:
            Optional[SpentBudgetResponse]: A dictionary containing
                the total spent budget.
        """
        body_dict = {"dataset_name": self.http_client.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_total_spent_budget", body)

        return validate_model_response_direct(res, SpentBudgetResponse)

    def get_remaining_budget(self) -> Optional[RemainingBudgetResponse]:
        """This function retrieves the remaining budget.

        Returns:
            Optional[RemainingBudgetResponse]: A dictionary
                containing the remaining budget.
        """
        body_dict = {"dataset_name": self.http_client.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_remaining_budget", body)

        return validate_model_response_direct(res, RemainingBudgetResponse)

    def get_previous_queries(self) -> Optional[List[dict]]:
        """This function retrieves the previous queries of the user.

        Raises:
            ValueError: If an unknown query type is encountered
                during deserialization.

        Returns:
            Optional[List[dict]]: A list of dictionary containing
            the different queries on the private dataset.
        """
        body_dict = {"dataset_name": self.http_client.dataset_name}

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
        return None

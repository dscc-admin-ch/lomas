from typing import Any, Protocol

import opendp.prelude as dp
import pandas as pd
import polars as pl
from csvw_eo.constants import COL_LIST, COL_NAME, MAXIMUM, MINIMUM, TABLE_SCHEMA
from csvw_eo.csvw_to_opendp_context import csvw_to_opendp_context
from csvw_eo.metadata_structure import TableMetadata
from fastapi import status
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
from lomas_client.models.config import ClientConfig
from lomas_client.utils import raise_error, validate_model_response_direct
from lomas_core.instrumentation import init_telemetry
from lomas_core.models.requests import GetDummyDataset, LomasRequestModel
from lomas_core.models.responses import Budget, DummyDsResponse, Job


class Bound(Protocol):
    """Any type that supports ordering comparisons (< and >)."""

    def __lt__(self, other: "Bound") -> bool: ...
    def __gt__(self, other: "Bound") -> bool: ...


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
                "Missing client config parameters."
                "If you are using this library from a managed environment and don't know "
                "about your credentials or other parameters, please contact your system administrator."
            ) from exc

        if self.config.telemetry.enabled:
            LoggingInstrumentor().instrument(set_logging_format=True)
            init_telemetry(self.config.telemetry)

        self.http_client = LomasHttpClient(self.config)
        self.smartnoise_sql = SmartnoiseSQLClient(self.http_client)
        self.opendp = OpenDPClient(self.http_client)
        self.diffprivlib = DiffPrivLibClient(self.http_client)

        self.metadata: dict[str, Any] | None = None

    def get_dataset_metadata(self) -> dict[str, Any]:
        """This function retrieves metadata for the dataset.

        Returns: A dictionary containing dataset metadata.
        """
        if self.metadata is None:
            body_dict = {"dataset_name": self.config.dataset_name}
            body = LomasRequestModel.model_validate(body_dict)
            res = self.http_client.post("get_dataset_metadata", body)
            if res.status_code == status.HTTP_200_OK:
                metadata = TableMetadata.model_validate(res.json())
                self.metadata = metadata.to_dict()
                return self.metadata

            raise_error(res)
        return self.metadata

    def get_column_metadata(self, column_name: str) -> dict[str, Any]:
        """This function retrieves metadata for the column.

        Returns: A dictionary containing column metadata.
        """
        if self.metadata is None:
            self.metadata = self.get_dataset_metadata()

        try:
            return next(col for col in self.metadata[TABLE_SCHEMA][COL_LIST] if col[COL_NAME] == column_name)
        except StopIteration as err:
            available = [col[COL_NAME] for col in self.metadata[TABLE_SCHEMA][COL_LIST]]
            raise ValueError(f"Column '{column_name}' not found. Available columns: {available}") from err

    def get_column_bounds[T: Bound](self, column_name: str) -> tuple[T, T]:
        """This function retrieves metadata  bounds for the column.

        Returns: A tuple of (minimum_bound, maximum_bound)
        """
        column = self.get_column_metadata(column_name)

        minimum = column.get(MINIMUM)
        maximum = column.get(MAXIMUM)

        if minimum is None or maximum is None:
            raise ValueError(f"Column '{column_name}' does not have bounds.")

        return minimum, maximum

    def get_diffprivlib_bounds(self, columns: list[str]) -> tuple[list[int | float], list[int | float]]:
        """Get bounds for a list of columns in diffprivlib expected format."""
        if self.metadata is None:
            self.metadata = self.get_dataset_metadata()

        cols = self.metadata[TABLE_SCHEMA][COL_LIST]
        col_map = {col[COL_NAME]: col for col in cols}

        lower, upper = [], []
        for col in columns:
            if col not in col_map:
                raise ValueError(f"Column '{col}' not found")

            metadata = col_map[col]

            if MINIMUM not in metadata or MAXIMUM not in metadata:
                raise ValueError(f"Column '{col}' does not have bounds")

            lower.append(metadata[MINIMUM])
            upper.append(metadata[MAXIMUM])

        return lower, upper

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
            dummy_df = DummyDsResponse.model_validate_json(data).dummy_df
            return pl.from_pandas(dummy_df).lazy() if lazy else dummy_df

        raise_error(res)

    def get_context(
        self,
        epsilon: float | None = None,
        delta: float | None = None,
        rho: float | None = None,
    ) -> dp.Context:
        """
        Create an OpenDP context based on a dummy dataset.

        This can be used to build an OpenDP pipeline locally on the client side.

        Args:
            epsilon (float | None, optional): Privacy parameter to be spent.
                Required for pure DP or approximate DP (Laplace mechanism).
                Defaults to None.
            delta (float | None, optional): Required if the pipeline measurement
                uses ZeroConcentratedDivergence (e.g., with make_gaussian) and is
                converted to SmoothedMaxDivergence using
                make_zCDP_to_approxDP. See:
                https://docs.smartnoise.org/sql/advanced.html#postprocess
                Defaults to None.
            rho (float | None, optional): Privacy parameter used for zCDP or
                approximate zCDP (Gaussian mechanism). Cannot be used if
                epsilon is provided.

        Returns:
            dp.Context: OpenDP context object initialized with metadata and
            user-provided privacy parameters.
        """
        dummy_lf = self.get_dummy_dataset(lazy=True)
        if self.metadata is None:
            self.metadata = self.get_dataset_metadata()

        return csvw_to_opendp_context(
            self.metadata, dummy_lf, epsilon=epsilon, delta=delta, rho=rho, split_evenly_over=1
        )

    def get_initial_budget(self) -> Budget:
        """This function retrieves the initial budget.

        Returns:
            Budget: A dictionary
                containing the initial budget.
        """
        body_dict = {"dataset_name": self.config.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_initial_budget", body)

        return validate_model_response_direct(res, Budget)

    def get_total_spent_budget(self) -> Budget:
        """This function retrieves the total spent budget.

        Returns:
            Budget: A dictionary containing
                the total spent budget.
        """
        body_dict = {"dataset_name": self.config.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_total_spent_budget", body)

        return validate_model_response_direct(res, Budget)

    def get_remaining_budget(self) -> Budget:
        """This function retrieves the remaining budget.

        Returns:
            Budget: A dictionary
                containing the remaining budget.
        """
        body_dict = {"dataset_name": self.config.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_remaining_budget", body)

        return validate_model_response_direct(res, Budget)

    def get_previous_queries(self) -> list[Job]:
        """This function retrieves the previous queries of the user.

        Raises:
            ValueError: If an unknown query type is encountered
                during deserialization.

        Returns:
            List[Job]: A list of all archived jobs for this user and dataset.
        """
        body_dict = {"dataset_name": self.config.dataset_name}

        body = LomasRequestModel.model_validate(body_dict)
        res = self.http_client.post("get_previous_queries", body)

        if res.status_code == status.HTTP_200_OK:
            jobs = [Job.model_validate(item) for item in res.json()]
            return jobs

        raise_error(res)

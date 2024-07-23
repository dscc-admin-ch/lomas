import random
from typing import List

import numpy as np
import pandas as pd
from snsynth import Synthesizer
from snsynth.transform import AnonymizationTransformer, MinMaxTransformer
from snsynth.transform.table import TableTransformer

from constants import (
    DEFAULT_NB_SYNTHETIC_SAMPLES,
    DPLibraries,
    SSynthTableTransStyle,
)
from dp_queries.dp_querier import DPQuerier
from utils.collections_models import Metadata
from utils.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from utils.input_models import SmartnoiseSynthModel, SmartnoiseSynthModelCost


class SmartnoiseSynthQuerier(DPQuerier):
    """
    Concrete implementation of the DPQuerier ABC for the SmartNoiseSynth library.
    """

    def cost(
        self, query_json: SmartnoiseSynthModelCost
    ) -> tuple[float, float]:
        """Return cost of query

        Args:
            query_json (SmartnoiseSynthModelCost): JSON request object for the query.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
        """
        # synth.odometer.spent
        return query_json.epsilon, query_json.delta

    def _get_data_transformer(
        self,
        metadata: Metadata,
        select_cols: List[str],
        nullable: bool,
        table_transformer_style: SSynthTableTransStyle,
    ) -> TableTransformer:
        """
        Creates the transformer based on the metadata.
        The transformer is used to transform the data before synthesis and then
        reverse the transformation after synthesis.
        See https://docs.smartnoise.org/synth/transforms/index.html
        Sort the column in three categories (categorical, ordinal and continuous)
        based on their types and metadata.

        Args:
            metadata (Metadata): Metadata of the dataset
            select_cols (List[str]): List of columns to select

        Returns:
            table_tranformer (TableTransformer) to pre and post-process the data
        """
        constraints = {}
        for col_name, data in metadata["columns"].items():
            if select_cols and col_name not in select_cols:
                continue

            if data["private_id"]:
                constraints[col_name] = AnonymizationTransformer(
                    lambda: random.randint(0, 1_000)
                )  # TODO: parameter
                continue

            match data["type"]:
                case "string":
                    constraints[col_name] = "categorical"
                case "boolean":
                    constraints[col_name] = "categorical"
                case "int":
                    if data["lower"]:
                        constraints[col_name] = MinMaxTransformer(
                            lower=data["lower"], upper=data["upper"]
                        )
                    elif data["cardinality"]:
                        constraints[col_name] = "categorical"
                    else:
                        constraints[col_name] = "ordinal"
                case "float":
                    constraints[col_name] = MinMaxTransformer(
                        lower=data["lower"], upper=data["upper"]
                    )
                case "datetime":
                    constraints[col_name] = "categorical"  # TODO: check
                case _:
                    raise InternalServerException(
                        f"unknown column type in metadata: \
                        {data['type']} in column {col_name}"
                    )

        self.transformer = TableTransformer.create(
            data=self.private_data,
            style=table_transformer_style,
            nullable=nullable,
            constraints=constraints,
        )

    def _preprocess_data(
        self, select_cols: List[str], mul_matrix: List
    ) -> None:
        if select_cols:
            try:
                self.private_data = self.private_data[select_cols]
            except KeyError as e:
                raise InvalidQueryException(
                    "Error while selecting provided select_cols: " + str(e)
                ) from e

        if mul_matrix:
            try:
                np_matrix = np.array(mul_matrix)
                mul_private_data = self.private_data.to_numpy().dot(
                    np_matrix.T
                )
                self.private_data = pd.DataFrame(mul_private_data)
            except ValueError as e:
                raise InvalidQueryException(
                    f"Failed to multiply provided mul_matrix: {(str(e))}"
                ) from e

    def _fit(self, nullable: bool) -> None:

        try:
            self.model = self.model.fit(
                data=self.private_data,
                transformer=self.transformer,
                preprocessor_eps=0.0,
                nullable=nullable,
            )
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error fitting model:" + str(e)
            ) from e

    def _sample(
        self, nb_samples: int, condition: str, mul_matrix: np.array
    ) -> pd.DataFrame:
        # Sample based on condition
        samples = (
            self.model.sample_conditional(nb_samples, condition)
            if condition
            else self.model.sample(nb_samples)
        )

        # Format back
        samples_df = (
            pd.DataFrame(samples)
            if mul_matrix
            else pd.DataFrame(samples, columns=self.private_data.columns)
        )
        return samples_df

    def query(self, query_json: SmartnoiseSynthModel) -> pd.DataFrame:
        """Perform the query and return the response.

        Args:
            query_json (SmartnoiseSynthModel): The JSON request object for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
            InvalidQueryException: If the budget values are too small to
                perform the query.

        Returns:
            pd.DataFrame: The resulting pd.DataFrame samples.
        """
        # Preprocessing information from metadata
        metadata = self.private_dataset.get_metadata()
        self.private_data = self.private_dataset.get_pandas_df()

        self._get_data_transformer(
            metadata,
            query_json.select_cols,
            query_json.nullable,
            query_json.table_transformer_style,
        )
        self._preprocess_data(query_json.select_cols, query_json.mul_matrix)

        # Preprocessing budget

        # Create and fit synthesizer
        self.model = Synthesizer.create(
            query_json.model,
            epsilon=query_json.epsilon,
            delta=query_json.delta,
        )
        self._fit(query_json.nullable)

        # Sample from synthesizer
        nb_samples = (
            query_json.nb_samples
            or metadata.nb_row
            or DEFAULT_NB_SYNTHETIC_SAMPLES
        )
        samples_df = self._sample(
            nb_samples, query_json.condition, query_json.mul_matrix
        )

        return samples_df

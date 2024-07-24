from typing import Dict, List

import numpy as np
import pandas as pd
from snsynth import Synthesizer
from snsynth.transform import (
    AnonymizationTransformer,
    BinTransformer,
    ChainTransformer,
    DateTimeTransformer,
    LabelTransformer,
    MinMaxTransformer,
    OneHotEncoder,
)
from snsynth.transform.table import TableTransformer

from constants import (
    DEFAULT_NB_SYNTHETIC_SAMPLES,
    DPLibraries,
    SSynthTableTransStyle,
)
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
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

    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        """Initializer.

        Args:
            private_dataset (PrivateDataset): Private dataset to query.
        """
        super().__init__(private_dataset)
        self.transformer = None
        self.private_data = None
        self.model = None

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

    def _get_column_by_types(
        self,
        metadata: Metadata,
        select_cols: List[str],
    ) -> Dict[str, List[str]]:
        """
        Sort the column in categories based on their types and metadata

        Args:
            metadata (Metadata): Metadata of the dataset
            select_cols (List[str]): List of columns to select

        Returns:
            Tuple[List]: Tuple of list os columns by categories
        """
        col_categories: Dict[str, List[str]] = {
            "categorical": [],
            "continuous": [],
            "datetime": [],
            "ordinal": [],
            "uuids": [],
        }
        for col_name, data in metadata["columns"].items():
            if select_cols and col_name not in select_cols:
                continue

            if data["private_id"]:
                col_categories["uuids"].append(col_name)
                continue

            # Sort the column in categories based on their types and metadata
            match data["type"]:
                case "string" | "boolean":
                    col_categories["categorical"].append(col_name)
                case "int" | "float":
                    if data["lower"]:
                        col_categories["continuous"].append(col_name)
                    elif data["cardinality"]:
                        col_categories["categorical"].append(col_name)
                    else:
                        col_categories["ordinal"].append(col_name)
                case "datetime":
                    col_categories["datetime"].append(col_name)
                case _:
                    raise InternalServerException(
                        f"Unknown column type in metadata: \
                        {data['type']} in column {col_name}"
                    )
        return col_categories

    def _prepare_data_transformer(
        self,
        metadata: Metadata,
        select_cols: List[str],
        nullable: bool,
        table_transformer_style: SSynthTableTransStyle,
    ) -> TableTransformer:
        """
        Creates the transformer based on the metadata
        The transformer is used to transform the data before synthesis and then
        reverse the transformation after synthesis.
        See https://docs.smartnoise.org/synth/transforms/index.html for documentation
        See https://github.com/opendp/smartnoise-sdk/blob/main/synth/snsynth/
            transform/type_map.py#L40 for get_transformer() method taken as basis.

        Args:
            metadata (Metadata): Metadata of the dataset
            select_cols (List[str]): List of columns to select
            nullable (bool): True is the data can have Null values, False otherwise
            table_transformer_style: 'gan' or 'cube'

        Returns:
            table_tranformer (TableTransformer) to pre and post-process the data
        """
        col_categories = self._get_column_by_types(metadata, select_cols)

        constraints = {}
        for col in col_categories["uuids"]:
            constraints[col] = AnonymizationTransformer("uuid4")

        for col in col_categories["categorical"]:
            if table_transformer_style == SSynthTableTransStyle.GAN:
                constraints[col] = ChainTransformer(
                    [LabelTransformer(nullable=nullable), OneHotEncoder()]
                )
            else:
                constraints[col] = LabelTransformer(nullable=nullable)

        for col in col_categories["datetime"]:
            if table_transformer_style == SSynthTableTransStyle.GAN:
                constraints[col] = ChainTransformer(
                    [
                        DateTimeTransformer(),
                        MinMaxTransformer(nullable=nullable),
                    ]
                )
            else:
                constraints[col] = ChainTransformer(
                    [
                        DateTimeTransformer(),
                        BinTransformer(bins=20, nullable=nullable),
                    ]
                )

        for col in col_categories["ordinal"]:
            if table_transformer_style == SSynthTableTransStyle.GAN:
                constraints[col] = ChainTransformer(
                    [LabelTransformer(nullable=nullable), OneHotEncoder()]
                )
            else:
                constraints[col] = LabelTransformer(nullable=nullable)

        for col in col_categories["continuous"]:
            if table_transformer_style == SSynthTableTransStyle.GAN:
                constraints[col] = MinMaxTransformer(
                    lower=metadata["columns"][col]["lower"],
                    upper=metadata["columns"][col]["upper"],
                    nullable=nullable,
                )
            else:
                constraints[col] = BinTransformer(nullable=nullable)

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

        self._prepare_data_transformer(
            metadata,
            query_json.select_cols,
            query_json.nullable,
            query_json.table_transformer_style,
        )
        self._preprocess_data(query_json.select_cols, query_json.mul_matrix)

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

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

from constants import (  # SSYNTH_DEFAULT_NB_SAMPLES,
    SSYNTH_PRIVATE_COLUMN,
    DPLibraries,
    SSynthColumnType,
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
        # model.odometer.spent
        return query_json.epsilon, query_json.delta

    def _categorize_column(self, data: dict) -> str:
        """
        Categorize the column based on its metadata.

        Args:
            data (dict): Metadata of the column.

        Returns:
            str: Category of the column.
        """
        match data["type"]:
            case "string" | "boolean":
                return SSynthColumnType.CATEGORICAL
            case "int" | "float":
                if "lower" in data.keys():
                    return SSynthColumnType.CONTINUOUS
                if "cardinality" in data.keys():
                    return SSynthColumnType.CATEGORICAL
                return SSynthColumnType.ORDINAL
            case "datetime":
                return SSynthColumnType.DATETIME
            case _:
                raise InternalServerException(
                    f"Unknown column type in metadata: {data['type']}"
                )

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
            Dict[str, List[str]]: Dictionnary of list of columns by categories
        """
        col_categories: Dict[str, List[str]] = {
            SSynthColumnType.CATEGORICAL: [],
            SSynthColumnType.CONTINUOUS: [],
            SSynthColumnType.DATETIME: [],
            SSynthColumnType.ORDINAL: [],
            SSynthColumnType.PRIVATE_ID: [],
        }
        for col_name, data in metadata["columns"].items():
            if select_cols and col_name not in select_cols:
                continue

            if "private_id" in data.keys():
                col_categories[SSynthColumnType.PRIVATE_ID].append(col_name)
                continue

            # Sort the column in categories based on their types and metadata
            category = self._categorize_column(data)
            col_categories[category].append(col_name)

        return col_categories

    def _prepare_data_transformer(
        self,
        metadata: Metadata,
        private_data: pd.DataFrame,
        query_json: dict,
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
            private_data
            query_json (SmartnoiseSynthModelCost): JSON request object for the query
                select_cols (List[str]): List of columns to select
                nullable (bool): True is the data can have Null values, False otherwise
                table_transformer_style: 'gan' or 'cube'

        Returns:
            table_tranformer (TableTransformer) to pre and post-process the data
        """
        col_categories = self._get_column_by_types(
            metadata, query_json.select_cols
        )
        style = query_json.table_transformer_style
        nullable = query_json.nullable

        constraints = {}
        for col in col_categories[SSynthColumnType.PRIVATE_ID]:
            constraints[col] = AnonymizationTransformer(SSYNTH_PRIVATE_COLUMN)

        if style == SSynthTableTransStyle.GAN:
            for col in col_categories[SSynthColumnType.CATEGORICAL]:
                constraints[col] = ChainTransformer(
                    [LabelTransformer(nullable=nullable), OneHotEncoder()]
                )
            for col in col_categories[SSynthColumnType.CONTINUOUS]:
                constraints[col] = MinMaxTransformer(
                    lower=metadata["columns"][col]["lower"],
                    upper=metadata["columns"][col]["upper"],
                    nullable=nullable,
                )
            for col in col_categories[SSynthColumnType.DATETIME]:
                constraints[col] = ChainTransformer(
                    [
                        DateTimeTransformer(),
                        MinMaxTransformer(
                            lower=metadata["columns"][col]["lower"],
                            upper=metadata["columns"][col]["upper"],
                            nullable=nullable,
                        ),
                    ]
                )
            for col in col_categories[SSynthColumnType.ORDINAL]:
                constraints[col] = ChainTransformer(
                    [LabelTransformer(nullable=nullable), OneHotEncoder()]
                )
        else:
            for col in col_categories[SSynthColumnType.CATEGORICAL]:
                constraints[col] = LabelTransformer(nullable=nullable)
            for col in col_categories[SSynthColumnType.CONTINUOUS]:
                constraints[col] = BinTransformer(nullable=nullable)
            for col in col_categories[SSynthColumnType.DATETIME]:
                constraints[col] = ChainTransformer(
                    [
                        DateTimeTransformer(),
                        BinTransformer(bins=20, nullable=nullable),
                    ]
                )
            for col in col_categories[SSynthColumnType.ORDINAL]:
                constraints[col] = LabelTransformer(nullable=nullable)

        return TableTransformer.create(
            data=private_data,
            style=style,
            nullable=nullable,
            constraints=constraints,
        )

    def _preprocess_data(
        self,
        private_data: pd.DataFrame,
        query_json: dict,
    ) -> pd.DataFrame:
        """
        Preprocess the data based on the query parameters.

        Args:
            private_data (pd.DataFrame): Private data to be preprocessed
            query_json (dict): (SmartnoiseSynthModelCost): JSON request object
                select_cols (List[str]): List of columns to select
                mul_matrix (List): Multiplication matrix for columns aggregations

        Returns:
            pd.DataFrame: Preprocessed private data
        """
        if query_json.select_cols:
            try:
                private_data = private_data[query_json.select_cols]
            except KeyError as e:
                raise InvalidQueryException(
                    "Error while selecting provided select_cols: " + str(e)
                ) from e

        if query_json.mul_matrix:
            try:
                np_matrix = np.array(query_json.mul_matrix)
                mul_private_data = private_data.to_numpy().dot(np_matrix.T)
                private_data = pd.DataFrame(mul_private_data)
            except ValueError as e:
                raise InvalidQueryException(
                    f"Failed to multiply provided mul_matrix: {(str(e))}"
                ) from e
        return private_data

    def _get_fit_model(
        self,
        private_data: pd.DataFrame,
        transformer: TableTransformer,
        query_json: dict,
    ) -> Synthesizer:
        """
        Create and fit the synthesizer model.

        Args:
            private_data (pd.DataFrame): Private data for fitting the model
            transformer (TableTransformer): Transformer to pre/postprocess data
            query_json (SmartnoiseSynthModelCost): JSON request object for the query
                synth_name (str): name of the Yanthesizer model to use
                epsilon (float): epsilon budget value
                delta (float): delta budget value
                nullable (bool): True if some data cells may be null
                synth_params (dict): Keyword arguments to pass to the synthesizer
                    constructor.

        Returns:
            Synthesizer: Fitted synthesizer model
        """
        if query_json.delta:  # not all model take delta as argument
            query_json.synth_params["delta"] = query_json.delta

        model = Synthesizer.create(
            synth=query_json.synth_name,
            epsilon=query_json.epsilon,
            verbose=True,
            kwargs=query_json.synth_params,
        )

        try:
            model.fit(
                data=private_data,
                transformer=transformer,
                preprocessor_eps=0.0,  # will error if not 0.
                nullable=query_json.nullable,
            )
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error fitting model:" + str(e)
            ) from e

        return model

    def _sample(
        self,
        model: Synthesizer,
        nb_samples: int,
        query_json: dict,
        colnames: list,
    ) -> pd.DataFrame:
        """
        Sample data from the fitted synthesizer model.

        Args:
            model (Synthesizer): Fitted synthesizer model
            nb_samples (int): Number of samples to generate
            query_json (dict): Request body from user with
                condition (Optional[str]): sampling condition
                mul_matrix (List): Multiplication matrix for columns aggregations
            colnames (list): List of column names for the samples

        Returns:
            pd.DataFrame: DataFrame of sampled data
        """
        # Sample based on condition
        samples = (
            model.sample_conditional(nb_samples, query_json.condition)
            if query_json.condition
            else model.sample(nb_samples)
        )

        # Format back
        samples_df = (
            pd.DataFrame(samples)
            if query_json.mul_matrix
            else pd.DataFrame(samples, columns=colnames)
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
        private_data = self.private_dataset.get_pandas_df()
        transformer = self._prepare_data_transformer(
            metadata, private_data, query_json
        )

        # Prepare private data
        private_data = self._preprocess_data(private_data, query_json)

        # Create and fit synthesizer
        model = self._get_fit_model(private_data, transformer, query_json)

        # # Sample from synthesizer
        # nb_samples = (
        #     query_json.nb_samples
        #     or metadata.nb_row
        #     or SSYNTH_DEFAULT_NB_SAMPLES
        # )
        # samples_df = self._sample(
        #     model, nb_samples, query_json, private_data.columns
        # )

        # return samples_df.to_dict(orient="tight")
        return model

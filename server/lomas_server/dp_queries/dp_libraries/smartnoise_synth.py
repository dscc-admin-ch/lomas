import re
from datetime import datetime
from typing import Dict, List, Optional, Union

import pandas as pd
from smartnoise_synth_logger import deserialise_constraints
from snsynth import Synthesizer
from snsynth.transform import (
    AnonymizationTransformer,
    BinTransformer,
    ChainTransformer,
    LabelTransformer,
    MinMaxTransformer,
    OneHotEncoder,
)
from snsynth.transform.datetime import DateTimeTransformer
from snsynth.transform.table import TableTransformer

from constants import (
    DEFAULT_DATE_FORMAT,
    SECONDS_IN_A_DAY,
    SSYNTH_DEFAULT_BINS,
    SSYNTH_PRIVATE_COLUMN,
    DPLibraries,
    SSynthColumnType,
    SSynthGanSynthesizer,
    SSynthMarginalSynthesizer,
    SSynthTableTransStyle,
)
from dp_queries.dp_libraries.utils import serialise_model
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.collection_models import Metadata
from utils.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from utils.query_models import (
    SmartnoiseSynthCostModel,
    SmartnoiseSynthQueryModel,
)


def datetime_to_float(upper, lower):
    """Convert the upper date as the distance between the upper date and
    lower date as float

    Args:
            upper (str): date to convert
            lower (str): start date to convert from

        Returns:
            float: number of days between upper and lower
    """
    distance = datetime.strptime(
        upper, DEFAULT_DATE_FORMAT
    ) - datetime.strptime(lower, DEFAULT_DATE_FORMAT)
    return float(distance.total_seconds() / SECONDS_IN_A_DAY)


class SmartnoiseSynthQuerier(DPQuerier):
    """
    Concrete implementation of the DPQuerier ABC for the SmartNoiseSynth library.
    """

    def __init__(self, private_dataset: PrivateDataset) -> None:
        super().__init__(private_dataset)
        self.model: Optional[Synthesizer] = None

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
                if "cardinality" in data.keys():
                    return SSynthColumnType.CATEGORICAL
                if "lower" in data.keys():
                    return SSynthColumnType.CONTINUOUS
                return SSynthColumnType.CATEGORICAL  # ordinal is categorical
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

    def _get_default_constraints(
        self,
        metadata: Metadata,
        query_json: dict,
        table_transformer_style: str,
    ) -> TableTransformer:
        """
        Get the defaults table transformer constraints based on the metadata
        See https://docs.smartnoise.org/synth/transforms/index.html for documentation
        See https://github.com/opendp/smartnoise-sdk/blob/main/synth/snsynth/
            transform/type_map.py#L40 for get_transformer() method taken as basis.

        Args:
            metadata (Metadata): Metadata of the dataset
            query_json (SmartnoiseSynthModelCost): JSON request object for the query
                select_cols (List[str]): List of columns to select
                nullable (bool): True is the data can have Null values, False otherwise
            table_transformer_style (str): 'gan' or 'cube'

        Returns:
            table_tranformer (TableTransformer) to pre and post-process the data
        """
        col_categories = self._get_column_by_types(
            metadata, query_json.select_cols
        )

        constraints = {}
        for col in col_categories[SSynthColumnType.PRIVATE_ID]:
            constraints[col] = AnonymizationTransformer(SSYNTH_PRIVATE_COLUMN)

        nullable = query_json.nullable
        if table_transformer_style == SSynthTableTransStyle.GAN:  # gan
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
                        DateTimeTransformer(
                            epoch=metadata["columns"][col]["lower"]
                        ),
                        MinMaxTransformer(
                            lower=0.0,  # because start epoch at lower bound
                            upper=datetime_to_float(
                                metadata["columns"][col]["upper"],
                                metadata["columns"][col]["lower"],
                            ),
                            nullable=nullable,
                        ),
                    ]
                )
        else:  # cube
            for col in col_categories[SSynthColumnType.CATEGORICAL]:
                constraints[col] = LabelTransformer(nullable=nullable)
            for col in col_categories[SSynthColumnType.CONTINUOUS]:
                constraints[col] = BinTransformer(
                    lower=metadata["columns"][col]["lower"],
                    upper=metadata["columns"][col]["upper"],
                    bins=SSYNTH_DEFAULT_BINS,
                    nullable=nullable,
                )
            for col in col_categories[SSynthColumnType.DATETIME]:
                constraints[col] = ChainTransformer(
                    [
                        DateTimeTransformer(
                            epoch=metadata["columns"][col]["lower"]
                        ),
                        BinTransformer(
                            lower=0.0,  # because start epoch at lower bound
                            upper=datetime_to_float(
                                metadata["columns"][col]["upper"],
                                metadata["columns"][col]["lower"],
                            ),
                            bins=SSYNTH_DEFAULT_BINS,
                            nullable=nullable,
                        ),
                    ]
                )

        return constraints

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
                nullable (bool): True if some data cells may be null
                synth_params (dict): Keyword arguments to pass to the synthesizer
                    constructor.

        Returns:
            Synthesizer: Fitted synthesizer model
        """
        if query_json.delta is not None:
            query_json.synth_params["delta"] = query_json.delta

        if query_json.synth_name == SSynthGanSynthesizer.DP_CTGAN:
            query_json.synth_params["disabled_dp"] = False

        try:
            model = Synthesizer.create(
                synth=query_json.synth_name,
                epsilon=query_json.epsilon,
                **query_json.synth_params,
            )
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error creating model: " + str(e)
            ) from e

        try:
            model.fit(
                data=private_data,
                transformer=transformer,
                preprocessor_eps=0.0,  # will error if not 0.0
                nullable=query_json.nullable,
            )
        except ValueError as e:  # Improve error message
            pattern = (
                r"sample_rate=[\d\.]+ is not a valid value\. "
                r"Please provide a float between 0 and 1\."
            )
            if (
                query_json.synth_name == SSynthGanSynthesizer.DP_CTGAN
                and re.match(pattern, str(e))
            ):
                raise ExternalLibraryException(
                    DPLibraries.SMARTNOISE_SYNTH,
                    f"Error fitting model: {e} Try decreasing batch_size in "
                    + "synth_params (default batch_size=500).",
                ) from e
            if (
                query_json.synth_name == SSynthGanSynthesizer.PATE_GAN
                and str(e) == "number sections must be larger than 0."
            ):
                # Need at least 1000 rows. Privacy breach ?
                raise ExternalLibraryException(
                    DPLibraries.SMARTNOISE_SYNTH,
                    f"{SSynthGanSynthesizer.PATE_GAN} not possible with this dataset.",
                ) from e
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error fitting model: " + str(e)
            ) from e
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error fitting model: " + str(e)
            ) from e
        return model

    def _model_pipeline(
        self, query_json: SmartnoiseSynthCostModel
    ) -> Synthesizer:
        """Return a trained Synthesizer model based on query_json

        Args:
            query_json (SmartnoiseSynthCostModel): JSON request object for the query.

        Returns:
            model: Smartnoise Synthesizer
        """
        # Table Transformation depenps on the tpe of Synthsizer
        if query_json.synth_name in [
            s.value for s in SSynthMarginalSynthesizer
        ]:
            table_transformer_style = SSynthTableTransStyle.CUBE
        else:
            table_transformer_style = SSynthTableTransStyle.GAN

        # Preprocessing information from metadata
        metadata = self.private_dataset.get_metadata()
        constraints = self._get_default_constraints(
            metadata, query_json, table_transformer_style
        )

        # Overwrite default constraint with custom constraint (if any)
        custom_constraints = query_json.constraints
        if custom_constraints:
            custom_constraints = deserialise_constraints(custom_constraints)
            custom_constraints = {
                key: custom_constraints[key]
                for key in query_json.select_cols
                if key in custom_constraints
            }
            constraints.update(custom_constraints)

        # Prepare private data
        private_data = self.private_dataset.get_pandas_df()
        if query_json.select_cols:
            try:
                private_data = private_data[query_json.select_cols]
            except KeyError as e:
                raise InvalidQueryException(
                    "Error while selecting provided select_cols: " + str(e)
                ) from e

        if query_json.synth_name == SSynthMarginalSynthesizer.MWEM:
            if private_data.shape[1] > 3:
                raise InvalidQueryException(  # TODO improve by looking better
                    "MWEMSynthesizer does not allow too high cardinality. Select "
                    + "less columns or put less bins in TableTransformer constraints."
                )

        # Get transformer
        transformer = TableTransformer.create(
            data=private_data,
            style=table_transformer_style,
            nullable=query_json.nullable,
            constraints=constraints,
        )

        # Create and fit synthesizer
        model = self._get_fit_model(private_data, transformer, query_json)
        return model

    def cost(
        self, query_json: SmartnoiseSynthCostModel
    ) -> tuple[float, float]:
        """Return cost of query_json

        Args:
            query_json (SmartnoiseSynthModelCost): JSON request object for the query.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
        # TODO: verify and model.rho
        """
        self.model = self._model_pipeline(query_json)
        if query_json.synth_name == SSynthMarginalSynthesizer.MWEM:
            epsilon, delta = self.model.epsilon, 0
        elif query_json.synth_name == SSynthGanSynthesizer.DP_CTGAN:
            epsilon, delta = self.model.epsilon_list[-1], self.model.delta
        else:
            epsilon, delta = self.model.epsilon, self.model.delta
        return epsilon, delta

    def query(
        self, query_json: SmartnoiseSynthQueryModel
    ) -> Union[pd.DataFrame, str]:
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
        if self.model is None:
            raise InternalServerException(
                "Smartnoise Synth `query` method called before `cost` method"
            )

        if not query_json.return_model:
            # Sample
            df_samples = (
                self.model.sample_conditional(
                    query_json.nb_samples, query_json.condition
                )
                if query_json.condition
                else self.model.sample(query_json.nb_samples)
            )

            # Ensure serialisable
            df_samples = df_samples.fillna("")
            return df_samples.to_dict(orient="records")

        return serialise_model(self.model)

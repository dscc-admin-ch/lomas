import re
from datetime import datetime
from typing import Dict, List, Optional, TypeAlias, TypeGuard, Union

import pandas as pd
from lomas_core.constants import (
    DPLibraries,
    SSynthGanSynthesizer,
    SSynthMarginalSynthesizer,
)
from lomas_core.error_handler import (
    ExternalLibraryException,
    InternalServerException,
    InvalidQueryException,
)
from lomas_core.models.collections import (
    BooleanMetadata,
    ColumnMetadata,
    DatetimeMetadata,
    FloatMetadata,
    IntCategoricalMetadata,
    IntMetadata,
    Metadata,
    StrCategoricalMetadata,
    StrMetadata,
)
from lomas_core.models.requests import (
    SmartnoiseSynthQueryModel,
    SmartnoiseSynthRequestModel,
)
from lomas_core.models.responses import SmartnoiseSynthModel, SmartnoiseSynthSamples
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

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.constants import (
    SECONDS_IN_A_DAY,
    SSYNTH_DEFAULT_BINS,
    SSYNTH_MIN_ROWS_PATE_GAN,
    SSYNTH_PRIVATE_COLUMN,
    SSynthTableTransStyle,
)
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_querier import DPQuerier


def datetime_to_float(upper: datetime, lower: datetime) -> float:
    """Convert the upper date as the distance between the upper date and.

    lower date as float

    Args:
            upper (datetime): date to convert
            lower (datetime): start date to convert from

        Returns:
            float: number of days between upper and lower
    """
    distance = upper - lower
    return float(distance.total_seconds() / SECONDS_IN_A_DAY)


# TODO maybe a better place to put this? See issue #336
SSynthColumnType: TypeAlias = Union[
    StrMetadata,
    StrCategoricalMetadata,
    BooleanMetadata,
    IntCategoricalMetadata,
    IntMetadata,
    FloatMetadata,
    DatetimeMetadata,
]


class SmartnoiseSynthQuerier(
    DPQuerier[
        SmartnoiseSynthRequestModel,
        SmartnoiseSynthQueryModel,
        SmartnoiseSynthSamples | SmartnoiseSynthModel,
    ]
):
    """Concrete implementation of the DPQuerier ABC for the SmartNoiseSynth library."""

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: AdminDatabase,
    ) -> None:
        super().__init__(data_connector, admin_database)
        self.model: Optional[Synthesizer] = None

    def _is_categorical(
        self, col_metadata: ColumnMetadata
    ) -> TypeGuard[
        StrMetadata | StrCategoricalMetadata | BooleanMetadata | IntCategoricalMetadata
    ]:
        """
        Checks if the column type is categorical.

        Args:
            col_metadata (ColumnMetadata): The column metadata

        Returns:
            TypeGuard[StrMetadata | StrCategoricalMetadata| BooleanMetadata |
                      IntCategoricalMetadata]:
                TypeGuard for categorical columns metadata
        """
        return isinstance(
            col_metadata,
            (
                StrMetadata,
                StrCategoricalMetadata,
                BooleanMetadata,
                IntCategoricalMetadata,
            ),
        )

    def _is_continuous(
        self, col_metadata: ColumnMetadata
    ) -> TypeGuard[IntMetadata | FloatMetadata]:
        """Checks if the column type is continuous.

        Args:
            col_metadata (ColumnMetadata): The column metadata

        Returns:
            TypeGuard[IntMetadata | FloatMetadata]:
                TypeGuard for continuous columns metadata
        """
        return isinstance(col_metadata, (IntMetadata, FloatMetadata))

    def _is_datetime(self, col_metadata: ColumnMetadata) -> TypeGuard[DatetimeMetadata]:
        """Checks if the column type is datetime.

        Args:
            col_metadata (ColumnMetadata): The column metadata

        Returns:
            TypeGuard[DatetimeMetadata]: TypeGuard for datetime metadata.
        """
        return isinstance(col_metadata, DatetimeMetadata)

    def _get_and_check_valid_column_types(
        self, metadata: Metadata, select_cols: List[str]
    ) -> Dict[str, SSynthColumnType]:
        """
        Ensures the type of the selected columns can be handled with.

        SmartnoiseSynth and returns the dict of column metadata
        for the selected columns.

        Args:
            metadata (Metadata): Dataset metadata
            select_cols (List[str]): List of selected columns

        Raises:
            InternalServerException: If one of the column types
                cannot be handled with SmartnoiseSynth.

        Returns:
            Dict[str, SSynthColumnType]: The filtered dict of selected columns.
        """
        columns: Dict[str, SSynthColumnType] = {}

        for col_name, data in metadata.columns.items():
            if select_cols and col_name not in select_cols:
                continue

            if not isinstance(data, SSynthColumnType):  # type: ignore[misc, arg-type]
                raise InternalServerException(
                    f"Column type {data.type} not supported for SmartnoiseSynth"
                )

            columns[col_name] = data

        return columns

    def _get_default_constraints(
        self,
        metadata: Metadata,
        query_json: SmartnoiseSynthRequestModel,
        table_transformer_style: str,
    ) -> TableTransformer:
        """
        Get the defaults table transformer constraints based on the metadata.

        See https://docs.smartnoise.org/synth/transforms/index.html for documentation
        See https://github.com/opendp/smartnoise-sdk/blob/main/synth/snsynth/
            transform/type_map.py#L40 for get_transformer() method taken as basis.

        Args:
            metadata (Metadata): Metadata of the dataset
            query_json (SmartnoiseSynthRequestModel): JSON request object for the query
                select_cols (List[str]): List of columns to select
                nullable (bool): True is the data can have Null values, False otherwise
            table_transformer_style (str): 'gan' or 'cube'

        Returns:
            table_tranformer (TableTransformer) to pre and post-process the data
        """
        columns = self._get_and_check_valid_column_types(
            metadata, query_json.select_cols
        )

        constraints = {}
        nullable = query_json.nullable
        for col, col_metadata in columns.items():
            if col_metadata.private_id:
                constraints[col] = AnonymizationTransformer(SSYNTH_PRIVATE_COLUMN)

            if table_transformer_style == SSynthTableTransStyle.GAN:  # gan
                if self._is_categorical(
                    col_metadata
                ):  # TODO any way of specifying cardinality? See issue #337
                    constraints[col] = ChainTransformer(
                        [LabelTransformer(nullable=nullable), OneHotEncoder()]
                    )
                elif self._is_continuous(col_metadata):
                    constraints[col] = MinMaxTransformer(
                        lower=col_metadata.lower,
                        upper=col_metadata.upper,
                        nullable=nullable,
                    )
                elif self._is_datetime(col_metadata):
                    constraints[col] = ChainTransformer(
                        [
                            DateTimeTransformer(epoch=col_metadata.lower),
                            MinMaxTransformer(
                                lower=0.0,  # because start epoch at lower bound
                                upper=datetime_to_float(
                                    col_metadata.upper,
                                    col_metadata.lower,
                                ),
                                nullable=nullable,
                            ),
                        ]
                    )
            else:  # Cube
                if self._is_categorical(
                    col_metadata
                ):  # TODO any way of specifying cardinality? See issue #337
                    constraints[col] = LabelTransformer(nullable=nullable)
                elif self._is_continuous(col_metadata):
                    constraints[col] = BinTransformer(
                        lower=col_metadata.lower,
                        upper=col_metadata.upper,
                        bins=SSYNTH_DEFAULT_BINS,
                        nullable=nullable,
                    )
                elif self._is_datetime(col_metadata):
                    constraints[col] = ChainTransformer(
                        [
                            DateTimeTransformer(epoch=col_metadata.lower),
                            BinTransformer(
                                lower=0.0,  # because start epoch at lower bound
                                upper=datetime_to_float(
                                    col_metadata.upper,
                                    col_metadata.lower,
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
        query_json: SmartnoiseSynthRequestModel,
    ) -> Synthesizer:
        """
        Create and fit the synthesizer model.

        Args:
            private_data (pd.DataFrame): Private data for fitting the model
            transformer (TableTransformer): Transformer to pre/postprocess data
            query_json (SmartnoiseSynthRequestModel): JSON request object for the query
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
        except ValueError as e:  # Improve snsynth error messages
            pattern = (
                r"sample_rate=[\d\.]+ is not a valid value\. "
                r"Please provide a float between 0 and 1\."
            )
            if query_json.synth_name == SSynthGanSynthesizer.DP_CTGAN and re.match(
                pattern, str(e)
            ):
                raise ExternalLibraryException(
                    DPLibraries.SMARTNOISE_SYNTH,
                    f"Error fitting model: {e} Try decreasing batch_size in "
                    + "synth_params (default batch_size=500).",
                ) from e
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error fitting model: " + str(e)
            ) from e
        except Exception as e:
            raise ExternalLibraryException(
                DPLibraries.SMARTNOISE_SYNTH, "Error fitting model: " + str(e)
            ) from e
        return model

    def _model_pipeline(self, query_json: SmartnoiseSynthRequestModel) -> Synthesizer:
        """Return a trained Synthesizer model based on query_json.

        Args:
            query_json (SmartnoiseSynthRequestModel): JSON request object for the query.

        Returns:
            model: Smartnoise Synthesizer
        """
        if (
            isinstance(query_json, SmartnoiseSynthQueryModel)
            and query_json.synth_name == SSynthMarginalSynthesizer.MST
            and query_json.return_model
        ):
            raise InvalidQueryException(
                "mst synthesizer cannot be returned, only samples. "
                + "Please, change model or set `return_model=False`"
            )
        if query_json.synth_name == SSynthMarginalSynthesizer.PAC_SYNTH:
            raise InvalidQueryException(
                "pacsynth synthesizer not supported due to Rust panic. "
                + "Please select another Synthesizer."
            )

        # Table Transformation depenps on the type of Synthesizer
        if query_json.synth_name in [s.value for s in SSynthMarginalSynthesizer]:
            table_transformer_style = SSynthTableTransStyle.CUBE
        else:
            table_transformer_style = SSynthTableTransStyle.GAN

        # Preprocessing information from metadata
        metadata = self.data_connector.get_metadata()
        if query_json.synth_name == SSynthGanSynthesizer.PATE_GAN:
            if metadata.rows < SSYNTH_MIN_ROWS_PATE_GAN:
                raise ExternalLibraryException(
                    DPLibraries.SMARTNOISE_SYNTH,
                    f"{SSynthGanSynthesizer.PATE_GAN} not reliable "
                    + "with this dataset.",
                )

        constraints = self._get_default_constraints(
            metadata, query_json, table_transformer_style
        )

        # Overwrite default constraint with custom constraint (if any)
        constraints_json = query_json.constraints
        if constraints_json:
            custom_constraints = deserialise_constraints(constraints_json)
            custom_constraints = {
                key: custom_constraints[key]
                for key in query_json.select_cols
                if key in custom_constraints
            }
            constraints.update(custom_constraints)

        # Prepare private data
        private_data = self.data_connector.get_pandas_df()
        if query_json.select_cols:
            try:
                private_data = private_data[query_json.select_cols]
            except KeyError as e:
                raise InvalidQueryException(
                    "Error while selecting provided select_cols: " + str(e)
                ) from e

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

    def cost(self, query_json: SmartnoiseSynthRequestModel) -> tuple[float, float]:
        """Return cost of query_json.

        Args:
            query_json (SmartnoiseSynthRequestModel): JSON request object for the query.

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
        self,
        query_json: SmartnoiseSynthQueryModel,
    ) -> SmartnoiseSynthSamples | SmartnoiseSynthModel:
        """Perform the query and return the response.

        Args:
            query_json (SmartnoiseSynthQueryModel):
                The request object for the query.

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
            return SmartnoiseSynthSamples(df_samples=df_samples)

        return SmartnoiseSynthModel(model=self.model)

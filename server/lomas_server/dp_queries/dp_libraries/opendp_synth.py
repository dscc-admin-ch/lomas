import opendp.prelude as dp
import polars as pl
from aio_pika.patterns.rpc import Proxy
from csvw_eo.csvw_to_opendp_context import csvw_to_opendp_context
from csvw_eo.datatypes import DataTypes

from lomas_core.constants import DPLibraries, OpenDPSynthAlgorithm
from lomas_core.exceptions import (
    ExternalLibraryException,
    InternalServerException,
)
from lomas_core.models.constants import get_lomas_logger
from lomas_core.models.requests import OpenDPSynthDataQueryModel, OpenDPSynthDataRequestModel
from lomas_core.models.responses import OpenDPPolarsQueryResult, OpenDPQueryResult
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_querier import DPQuerier

logger = get_lomas_logger(__name__)

# TODO: Move this to constants
# Idea is to reduce size of contigency_table
# Investigate if we want something dynaminc ? user can decide? etc.
#
DEFAULT_SYNTH_BINS = 10
MAX_INT_KEYS = 10


class OpenDPSynthQuerier(
    DPQuerier[OpenDPSynthDataQueryModel, OpenDPSynthDataRequestModel, OpenDPQueryResult]
):
    """TODO"""

    def __init__(
        self,
        data_connector: DataConnector,
        admin_database: Proxy,
    ) -> None:
        """Initializer.

        Args:
            data_connector (DataConnector): DataConnector for the dataset to query.
        """
        super().__init__(data_connector, admin_database)

        # Get metadata once and for all
        self.metadata = self.data_connector.metadata

    def _derive_keys_and_cuts(
        self,
        columns: list[str],  # Potentially let user filter columns ?
    ) -> tuple[dict[str, list], dict[str, list[float]]]:
        """TODO"""
        keys: dict[str, list] = {}
        cuts: dict[str, list[float]] = {}

        for col_meta in self.metadata.columns:
            col_name = col_meta.name
            if (columns is not None) and (col_name not in columns):
                # We skip if the columns is not specifically given by the user
                continue

            if col_meta.datatype == DataTypes.BOOLEAN:
                keys[col_name] = [True, False]
                continue

            # If categorical and keys are publically known, we can create keys using the metadata
            if col_meta.public_keys_values:
                keys[col_name] = [k.predicate.partition_value for k in col_meta.public_keys_values]
                continue

            # For int, if size of integer is not too big, we can create a list of integer
            # with full range of possibilites, otherwise we use bins
            if (
                col_meta.datatype in (DataTypes.INT, DataTypes.POSITIVE_INTEGER)
                and col_meta.minimum is not None
                and col_meta.maximum is not None
            ):
                lo, hi = int(col_meta.minimum), int(col_meta.maximum)
                n_values = hi - lo + 1
                if n_values <= MAX_INT_KEYS:
                    keys[col_name] = list(range(lo, hi + 1))
                    continue

            n_bins = getattr(col_meta, "synth_bins", DEFAULT_SYNTH_BINS)
            if col_meta.datatype in (DataTypes.DATE, DataTypes.DATETIME):
                # For now, not sure how to treat datetime with MST()
                continue

            if col_meta.minimum is not None and col_meta.maximum is not None:
                lo, hi = col_meta.minimum, col_meta.maximum
                step = (hi - lo) / n_bins

                if col_meta.datatype in (DataTypes.INT, DataTypes.POSITIVE_INTEGER):
                    raw_edges = [round(lo + i * step) for i in range(1, n_bins)]
                    cuts[col_name] = sorted(set(raw_edges))
                else:
                    cuts[col_name] = [lo + i * step for i in range(1, n_bins)]
                # Bin edges built from declared min/max, so exhaustive by construction.
                continue

        return keys, cuts

    def _build_synth_algorithm(self, query_json: OpenDPSynthDataRequestModel):
        """Translate the request's algorithm choice into an mbi.Algorithm."""
        match query_json.algorithm:
            case OpenDPSynthAlgorithm.AIM:
                return dp.mbi.AIM()
            case OpenDPSynthAlgorithm.MST:
                return dp.mbi.MST()
            case _:
                raise InternalServerException(f"Invalid synthetic data algorithm: {query_json.algorithm}")

    def query(self, query_json: OpenDPSynthDataRequestModel) -> OpenDPQueryResult:
        """TODO: Do docs"""
        input_data = self.data_connector.get_polars_lf()
        context = csvw_to_opendp_context(
            self.metadata.to_dict(),
            input_data,
            epsilon=query_json.epsilon,
            delta=query_json.delta,
            rho=query_json.rho,
            split_evenly_over=1,
        )
        algorithm = self._build_synth_algorithm(query_json)
        keys, cuts = self._derive_keys_and_cuts(query_json.columns)

        try:
            query = context.query()
            if query_json.columns is not None:
                query = query.select(query_json.columns)

            contingency_table = query.contingency_table(keys=keys, cuts=cuts, algorithm=algorithm)
            table = contingency_table.release()
            synth_df = table.synthesize()
        except Exception as e:
            logger.exception(e)
            raise ExternalLibraryException(
                DPLibraries.OPENDP_SYNTH, "Error releasing synthetic data:" + str(e)
            ) from e

        if isinstance(synth_df, pl.DataFrame):
            return OpenDPPolarsQueryResult(value=synth_df)
        return OpenDPQueryResult(value=synth_df)

    def cost(self, query):
        return (0, 0)

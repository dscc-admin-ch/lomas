import os

import opendp as dp
from aio_pika.patterns.rpc import Proxy
from opendp._lib import lib_path
from opendp.mod import enable_features

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import (
    ExternalLibraryException,
)
from lomas_core.models.constants import OpenDPFeatures, init_logging
from lomas_core.models.requests import OpenDPQueryModel, OpenDPRequestModel
from lomas_core.models.responses import OpenDPPolarsQueryResult, OpenDPQueryResult
from lomas_core.opendp_utils import deserialize_context_query
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_querier import DPQuerier

logger = init_logging(__name__)


class OpenDPQuerier(DPQuerier[OpenDPRequestModel, OpenDPQueryModel, OpenDPQueryResult]):
    """Concrete implementation of the DPQuerier ABC for the OpenDP library."""

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
        self.metadata = self.data_connector.metadata.model_dump()

    def cost(self, query_json: OpenDPRequestModel) -> tuple[float, float]:
        """
        Estimate cost of query.

        Args:
            query_json (OpenDPRequestModel): The request model object.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.
            InternalServerException: For any other unforseen exceptions.
            InvalidQueryException: The pipeline does not contain a
                "measurement", there is not enough budget or the dataset
                does not exist.

        Returns:
            tuple[float, float]: The tuple of costs, the first value
                is the epsilon cost, the second value is the delta value.
        """
        # TODO: this should be simplified with context

        # We can directly take what is given by user since the context will use
        # exactly what is given
        delta = query_json.delta if query_json.delta is not None else 0

        if query_json.rho:
            # TODO: create epilon equivalence
            return query_json.rho, delta

        return query_json.epsilon, delta

    def query(self, query_json: OpenDPQueryModel) -> OpenDPQueryResult | OpenDPPolarsQueryResult:
        """Perform the query and return the response.

        Args:
            query_json (OpenDPQueryModel): The input model for the query.

        Raises:
            ExternalLibraryException: For exceptions from libraries
                external to this package.

        Returns:
            (Union[List, int, float]) query result
        """
        input_data = self.data_connector.get_polars_lf()
        plan = deserialize_context_query(query_json, self.metadata, input_data)

        try:
            release_data = plan.release()
        except Exception as e:
            logger.exception(e)
            raise ExternalLibraryException(
                DPLibraries.OPENDP,
                "Error executing query:" + str(e),
            ) from e

        if isinstance(release_data, dp.extras.polars.OnceFrame):
            release_data = release_data.collect()
            return OpenDPPolarsQueryResult(value=release_data)
        return OpenDPQueryResult(value=release_data)


def set_opendp_features_config(features: OpenDPFeatures) -> None:
    """Enable opendp features based on config.

    See https://github.com/opendp/opendp/discussions/304

    Also sets the "OPENDP_POLARS_LIB_PATH" environment variable
    for correctly creating private lazyframes from deserialized
    polars plans.
    """
    for feat in features:
        logger.debug(f"OpenDP: enabling feature: {feat}")
        enable_features(feat)

    # Set DP Libraries config
    os.environ["OPENDP_LIB_PATH"] = str(lib_path)

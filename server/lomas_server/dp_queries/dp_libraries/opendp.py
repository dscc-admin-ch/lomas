import os
from base64 import b64decode

import opendp as dp
from aio_pika.patterns.rpc import Proxy
from csvw_eo.csvw_to_opendp_context import csvw_to_opendp_context
from opendp._lib import lib_path
from opendp.mod import enable_features

from lomas_core.constants import DPLibraries
from lomas_core.error_handler import ExternalLibraryException, InternalServerException, InvalidQueryException
from lomas_core.models.constants import OpenDPFeatures, get_lomas_logger
from lomas_core.models.requests import OpenDPQueryModel, OpenDPRequestModel
from lomas_core.models.responses import OpenDPPolarsQueryResult, OpenDPQueryResult
from lomas_server.constants import OpenDPMeasurement
from lomas_server.data_connector.data_connector import DataConnector
from lomas_server.dp_queries.dp_querier import DPQuerier

logger = get_lomas_logger(__name__)


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
        self.metadata = self.data_connector.metadata

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
        input_data = self.data_connector.get_polars_lf()
        context = csvw_to_opendp_context(
            self.metadata.to_dict(),
            input_data,
            epsilon=query_json.epsilon,
            delta=query_json.delta,
            rho=query_json.rho,
            split_evenly_over=1,
        )

        meas = context.accountant
        meas_type = str(meas.output_measure)
        max_contrib = self.metadata.max_contributions

        match meas_type:
            case OpenDPMeasurement.ZERO_CONCENTRATED_DIVERGENCE:
                meas_zcdp = dp.combinators.make_zCDP_to_approxDP(meas)
                cost = meas_zcdp.map(d_in=int(max_contrib))

                fixed_delta = query_json.delta
                if fixed_delta is None:
                    raise InvalidQueryException("Provide a fixed delta for this query.")
                epsilon, delta = cost.epsilon(fixed_delta), fixed_delta

            case OpenDPMeasurement.APPROX_ZERO_CONCENTRATED_DIVERGENCE:
                meas_zcdp = dp.combinators.make_zCDP_to_approxDP(meas)
                cost = meas_zcdp.map(d_in=int(max_contrib))

                epsilon, delta = cost[0].epsilon(cost[1]), cost[1]

            case OpenDPMeasurement.MAX_DIVERGENCE:
                epsilon, delta = meas.map(d_in=int(max_contrib)), 0

            case OpenDPMeasurement.APPROX_MAX_DIVERGENCE:
                epsilon, delta = meas.map(d_in=int(max_contrib))

            case _:
                raise InternalServerException(f"Invalid measurement type: {meas_type}")
        return epsilon, delta

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
        context = csvw_to_opendp_context(
            self.metadata.to_dict(),
            input_data,
            epsilon=query_json.epsilon,
            delta=query_json.delta,
            rho=query_json.rho,
            split_evenly_over=1,
        )
        serialized_plan = b64decode(query_json.opendp_json.encode("utf-8"))
        plan = context.deserialize_polars_plan(serialized_plan)

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

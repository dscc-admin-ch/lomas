import opendp as dp
import polars as pl
from returns.curry import partial
from returns.io import IOResultE
from returns.pipeline import flow
from returns.pointfree import map_

from lomas_client.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response
from lomas_core.constants import OpenDpMechanism, OpenDpPipelineType
from lomas_core.error_handler import InvalidQueryException
from lomas_core.models.requests import (
    OpenDPDummyQueryModel,
    OpenDPQueryModel,
    OpenDPRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse


class OpenDPClient:
    """A client for executing and estimating the cost of OpenDP queries."""

    def __init__(self, http_client: LomasHttpClient) -> None:
        self.http_client = http_client

    def _get_opendp_request_body(
        self,
        opendp_pipeline: dp.Measurement | pl.LazyFrame,
        fixed_delta: float | None = None,
        mechanism: OpenDpMechanism | None = OpenDpMechanism.LAPLACE,
    ) -> dict:
        """This function executes an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.\
                Can be a dp.Measurement or a polars LazyFrame (plan) for opendp.polars\
                pipelines.
            delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.\
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).\
                In that case a delta must be provided by the user.\
                Defaults to None.
            mechanism: (OpenDpMechanism, optional): Type of noise addition mechanism to use\
                in polars pipelines. "laplace" or "gaussian".
        Raises:
            Exception: If the opendp_pipeline type is not supported.
        Returns:
            dict: A dictionnary for the request body.
        """
        body_json = {
            "dataset_name": self.http_client.config.dataset_name,
            "fixed_delta": fixed_delta,
            "mechanism": mechanism,
        }

        if isinstance(opendp_pipeline, dp.Measurement):
            body_json["opendp_json"] = opendp_pipeline.to_json()
            body_json["pipeline_type"] = OpenDpPipelineType.LEGACY
        elif isinstance(opendp_pipeline, pl.LazyFrame):
            body_json["opendp_json"] = opendp_pipeline.serialize(format="json")
            body_json["pipeline_type"] = OpenDpPipelineType.POLARS
        else:
            raise InvalidQueryException(
                f"Opendp_pipeline must either of type Measurement or LazyFrame, found {type(opendp_pipeline)}"
            )

        return body_json

    def cost(
        self,
        opendp_pipeline: dp.Measurement | pl.LazyFrame,
        fixed_delta: float | None = None,
        mechanism: OpenDpMechanism | None = OpenDpMechanism.LAPLACE,
    ) -> CostResponse:
        """This function estimates the cost of executing an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.
            fixed_delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.\
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).\
                In that case a fixed_delta must be provided by the user.\
                Defaults to None.
            mechanism: (OpenDpMechanism, optional): Type of noise addition mechanism to use\
                in polars pipelines. "laplace" or "gaussian".
        Raises:
            Exception: If the opendp_pipeline type is not suppported.

        Returns:
            CostResponse: The estimated cost.
        """
        body_json = self._get_opendp_request_body(
            opendp_pipeline,
            fixed_delta=fixed_delta,
            mechanism=mechanism,
        )

        return flow(
            body_json,
            OpenDPRequestModel.model_validate,
            partial(self.http_client.post, "estimate_opendp_cost"),
            map_(lambda res: validate_model_response(self.http_client, res, CostResponse)),
        )

    def query(
        self,
        opendp_pipeline: dp.Measurement | pl.LazyFrame,
        fixed_delta: float | None = None,
        mechanism: OpenDpMechanism | None = OpenDpMechanism.LAPLACE,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> IOResultE[QueryResponse]:
        """This function executes an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query. \
                Can be a dp.Measurement or a polars LazyFrame (plan) for opendp.polars\
                pipelines.
            fixed_delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).
                In that case a fixed_delta must be provided by the user.
                Defaults to None.
            mechanism: (OpenDpMechanism, optional): Type of noise addition mechanism to use\
                in polars pipelines. "laplace" or "gaussian".
            dummy (bool, optional): Whether to use a dummy dataset. Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.\
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.\
            Defaults to DUMMY_SEED.

        Raises:
            Exception: If the opendp_pipeline type is not suppported.

        Returns:
            QueryResponse: A dictionary of the response body containing the deserialized pipeline result.
        """
        body_dict = self._get_opendp_request_body(
            opendp_pipeline,
            fixed_delta=fixed_delta,
            mechanism=mechanism,
        )

        if dummy:
            return flow(
                {**body_dict, "dummy_nb_rows": nb_rows, "dummy_seed": seed},
                OpenDPDummyQueryModel.model_validate,
                partial(self.http_client.post, "dummy_opendp_query"),
                map_(lambda res: validate_model_response(self.http_client, res, QueryResponse)),
            )
        return flow(
            body_dict,
            OpenDPQueryModel.model_validate,
            partial(self.http_client.post, "opendp_query"),
            map_(lambda res: validate_model_response(self.http_client, res, QueryResponse)),
        )

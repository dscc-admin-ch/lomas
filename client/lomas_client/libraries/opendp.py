from base64 import b64encode

import opendp as dp
import polars as pl

from lomas_client.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response
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
        opendp_pipeline: dp.extras.polars.LazyFrameQuery | pl.LazyFrame,
        epsilon: float | None = None,
        delta: float | None = None,
        rho: float | None = None,
        approx_zcdp: bool = True,
    ) -> dict:
        """This function executes an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.\
                Can be a dp.Measurement or a polars LazyFrame (plan) for opendp.polars\
                pipelines.
            epsilon (float): Privacy parameter that will be spent. For pure-DP or approximate DP\
                 this must be set. (Laplace mechanism)
            delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.\
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).\
                In that case a delta must be provided by the user.\
                Defaults to None.
            rho (float): Privacy parameter used for zCDP or approximate-zCDP (Gaussian mechanism).\
                 Cannot be used if epsilon is not None.
            approx_zcdp (bool): If false, delta is used to compute the epsilon consumption equivalent when user wants to use zCDP.
                Default True.
        Raises:
            Exception: If the opendp_pipeline type is not supported.
        Returns:
            dict: A dictionnary for the request body.
        """
        body_json = {
            "dataset_name": self.http_client.config.dataset_name,
            "epsilon": epsilon,
            "delta": delta,
            "rho": rho,
            "approx_zcdp": approx_zcdp,
        }

        if isinstance(opendp_pipeline, (pl.LazyFrame, dp.extras.polars.LazyFrameQuery)):
            body_json["opendp_json"] = b64encode(opendp_pipeline.serialize()).decode("utf-8")
        else:
            raise InvalidQueryException(
                f"Opendp_pipeline must be of type LazyFrame, found {type(opendp_pipeline)}"
            )

        return body_json

    def cost(
        self,
        opendp_pipeline: dp.extras.polars.LazyFrameQuery | pl.LazyFrame,
        epsilon: float | None = None,
        delta: float | None = None,
        rho: float | None = None,
        approx_zcdp: bool = True,
    ) -> CostResponse:
        """This function estimates the cost of executing an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.
            epsilon (float): Privacy parameter that will be spent. For pure-DP or approximate DP\
                 this must be set. (Laplace mechanism)
            delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.\
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).\
                In that case a delta must be provided by the user.\
                Defaults to None.
            rho (float): Privacy parameter used for zCDP or approximate-zCDP (Gaussian mechanism).\
                 Cannot be used if epsilon is not None.
            approx_zcdp (bool): If false, delta is used to compute the epsilon consumption equivalent when user wants to use zCDP.
                Default True.
        Raises:
            Exception: If the opendp_pipeline type is not suppported.

        Returns:
            CostResponse: The estimated cost.
        """
        body_json = self._get_opendp_request_body(
            opendp_pipeline,
            epsilon=epsilon,
            delta=delta,
            rho=rho,
            approx_zcdp=approx_zcdp,
        )
        body = OpenDPRequestModel.model_validate(body_json)
        res = self.http_client.post("estimate_opendp_cost", body)

        return validate_model_response(self.http_client, res, CostResponse)

    def query(
        self,
        opendp_pipeline: dp.extras.polars.LazyFrameQuery | pl.LazyFrame,
        epsilon: float | None = None,
        delta: float | None = None,
        rho: float | None = None,
        approx_zcdp: bool = True,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> QueryResponse:
        """This function executes an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query. \
                Can be a dp.Measurement or a polars LazyFrame (plan) for opendp.polars\
                pipelines.
            epsilon (float): Privacy parameter that will be spent. For pure-DP or approximate DP\
                 this must be set. (Laplace mechanism)
            delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).
                In that case a delta must be provided by the user.
                Defaults to None.
            rho (float): Privacy parameter used for zCDP or approximate-zCDP (Gaussian mechanism).\
                 Cannot be used if epsilon is not None.
            approx_zcdp (bool): If false, delta is used to compute the epsilon consumption equivalent when user wants to use zCDP.
                Default True.
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
        body_json = self._get_opendp_request_body(
            opendp_pipeline,
            epsilon=epsilon,
            delta=delta,
            rho=rho,
            approx_zcdp=approx_zcdp,
        )

        request_model: type[OpenDPRequestModel]
        if dummy:
            endpoint = "dummy_opendp_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
            request_model = OpenDPDummyQueryModel
        else:
            endpoint = "opendp_query"
            request_model = OpenDPQueryModel

        body = request_model.model_validate(body_json)
        res = self.http_client.post(endpoint, body)

        return validate_model_response(self.http_client, res, QueryResponse)

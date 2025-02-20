from typing import Optional, Type

import opendp as dp
import polars as pl

from lomas_client.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response
from lomas_core.constants import OpenDpMechanism
from lomas_core.models.requests import (
    OpenDPDummyQueryModel,
    OpenDPQueryModel,
    OpenDPRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse


class OpenDPClient:
    """A client for executing and estimating the cost of OpenDP queries."""

    def __init__(self, http_client: LomasHttpClient):
        self.http_client = http_client

    def _get_opendp_request_body(
        self,
        opendp_pipeline: dp.Measurement | pl.LazyFrame,
        fixed_delta: Optional[float] = None,
        mechanism: Optional[OpenDpMechanism] = "laplace",
    ):
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
            mechanism: (str, optional): Type of noise addition mechanism to use\
                in polars pipelines. "laplace" or "gaussian".
        Raises:
            Exception: If the opendp_pipeline type is not supported.
        Returns:
            dict: A dictionnary for the request body.
        """
        body_json = {
            "dataset_name": self.http_client.dataset_name,
            "fixed_delta": fixed_delta,
            "mechanism": mechanism,
        }

        if isinstance(opendp_pipeline, dp.Measurement):
            body_json["opendp_json"] = opendp_pipeline.to_json()
            body_json["pipeline_type"] = "legacy"
        elif isinstance(opendp_pipeline, pl.LazyFrame):
            body_json["opendp_json"] = opendp_pipeline.serialize(format="json")
            body_json["pipeline_type"] = "polars"
        else:
            raise TypeError(
                f"Opendp_pipeline must either of type Measurement"
                f" or LazyFrame, found {type(opendp_pipeline)}"
            )

        return body_json

    def cost(
        self,
        opendp_pipeline: dp.Measurement | pl.LazyFrame,
        fixed_delta: Optional[float] = None,
        mechanism: Optional[str] = "laplace",
    ) -> Optional[CostResponse]:
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
            mechanism: (str, optional): Type of noise addition mechanism to use\
                in polars pipelines. "laplace" or "gaussian".
        Raises:
            Exception: If the opendp_pipeline type is not suppported.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """

        body_json = self._get_opendp_request_body(
            opendp_pipeline,
            fixed_delta=fixed_delta,
            mechanism=mechanism,
        )
        body = OpenDPRequestModel.model_validate(body_json)
        res = self.http_client.post("estimate_opendp_cost", body)

        return validate_model_response(res, CostResponse)

    def query(
        self,
        opendp_pipeline: dp.Measurement | pl.LazyFrame,
        fixed_delta: Optional[float] = None,
        mechanism: Optional[str] = "laplace",
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[QueryResponse]:
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
            mechanism: (str, optional): Type of noise addition mechanism to use\
                in polars pipelines. "laplace" or "gaussian".
            dummy (bool, optional): Whether to use a dummy dataset. Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.\
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.\
            Defaults to DUMMY_SEED.

        Raises:
            Exception: If the opendp_pipeline type is not suppported.

        Returns:
            Optional[dict]: Optional[dict]: A dictionary of the response body\
                containing the deserialized pipeline result.
        """
        body_json = self._get_opendp_request_body(
            opendp_pipeline,
            fixed_delta=fixed_delta,
            mechanism=mechanism,
        )

        request_model: Type[OpenDPRequestModel]
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

        return validate_model_response(res, QueryResponse)

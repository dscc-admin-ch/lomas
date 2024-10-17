from typing import Optional, Type

import opendp as dp
from lomas_core.models.requests import (
    OpenDPDummyQueryModel,
    OpenDPQueryModel,
    OpenDPRequestModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse

from lomas_client.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response


class OpenDPClient:
    """A client for executing and estimating the cost of OpenDP queries."""

    def __init__(self, http_client: LomasHttpClient):
        self.http_client = http_client

    def cost(
        self,
        opendp_pipeline: dp.Measurement,
        fixed_delta: Optional[float] = None,
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

        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        opendp_json = opendp_pipeline.to_json()
        body_dict = {
            "dataset_name": self.http_client.dataset_name,
            "opendp_json": opendp_json,
            "fixed_delta": fixed_delta,
        }

        body = OpenDPRequestModel.model_validate(body_dict)
        res = self.http_client.post("estimate_opendp_cost", body)

        return validate_model_response(res, CostResponse)

    def query(
        self,
        opendp_pipeline: dp.Measurement,
        fixed_delta: Optional[float] = None,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[QueryResponse]:
        """This function executes an OpenDP query.

        Args:
            opendp_pipeline (dp.Measurement): The OpenDP pipeline for the query.
            fixed_delta (Optional[float], optional): If the pipeline measurement is of\
                type “ZeroConcentratedDivergence” (e.g. with make_gaussian) then it is\
                converted to “SmoothedMaxDivergence” with make_zCDP_to_approxDP\
                (`See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__).
                In that case a fixed_delta must be provided by the user.
                Defaults to None.
            dummy (bool, optional): Whether to use a dummy dataset. Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.\
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.\
            Defaults to DUMMY_SEED.

        Raises:
            Exception: If the server returns dataframes

        Returns:
            Optional[dict]: A Pandas DataFrame containing the query results.
        """
        opendp_json = opendp_pipeline.to_json()
        body_dict = {
            "dataset_name": self.http_client.dataset_name,
            "opendp_json": opendp_json,
            "fixed_delta": fixed_delta,
        }

        request_model: Type[OpenDPRequestModel]
        if dummy:
            endpoint = "dummy_opendp_query"
            body_dict["dummy_nb_rows"] = nb_rows
            body_dict["dummy_seed"] = seed
            request_model = OpenDPDummyQueryModel
        else:
            endpoint = "opendp_query"
            request_model = OpenDPQueryModel

        body = request_model.model_validate(body_dict)
        res = self.http_client.post(endpoint, body)

        return validate_model_response(res, QueryResponse)

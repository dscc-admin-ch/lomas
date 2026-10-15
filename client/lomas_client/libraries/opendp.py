from base64 import b64encode

import numpy as np
import opendp.prelude as dp
import polars as pl
from csvw_eo import XSD_GROUP_MAP, DataTypesGroups, TableMetadata

from lomas_client.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_client.http_client import LomasHttpClient
from lomas_client.utils import validate_model_response
from lomas_core.exceptions import InvalidQueryException
from lomas_core.models.requests import (
    OpenDPCostQueryModel,
    OpenDPDummyQueryModel,
    OpenDPQueryModel,
    OpenDPRequestModel,
    OpenDPSynthDataQueryModel,
)
from lomas_core.models.responses import CostResponse, QueryResponse


class OpenDPClient:
    """A client for executing and estimating the cost of OpenDP queries."""

    def __init__(self, http_client: LomasHttpClient, metadata: dict | None = None) -> None:
        self.http_client = http_client
        self.metadata = metadata

    def _get_opendp_request_body(
        self,
        opendp_pipeline: dp.polars.LazyFrameQuery | pl.LazyFrame,
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

        if isinstance(opendp_pipeline, (pl.LazyFrame, dp.polars.LazyFrameQuery)):
            body_json["opendp_json"] = b64encode(opendp_pipeline.serialize()).decode("utf-8")
        else:
            raise InvalidQueryException(
                f"Opendp_pipeline must be of type LazyFrame, found {type(opendp_pipeline)}"
            )

        return body_json

    def cost(
        self,
        opendp_pipeline: dp.polars.LazyFrameQuery | pl.LazyFrame,
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
        body = OpenDPCostQueryModel.model_validate(body_json)
        res = self.http_client.post("estimate_opendp_cost", body)

        return validate_model_response(self.http_client, res, CostResponse)

    def query(
        self,
        opendp_pipeline: dp.polars.LazyFrameQuery | pl.LazyFrame,
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

    def _gen_key_cuts(self) -> (dict, dict):
        keys, cuts = {}, {}
        for col in TableMetadata.from_dict(self.metadata).columns:
            if (pub_keys := col.public_keys_values) is not None:
                keys[col.name] = [pk.predicate.partition_value for pk in pub_keys]
            elif XSD_GROUP_MAP[col.datatype] in {DataTypesGroups.INTEGER, DataTypesGroups.FLOAT}:
                cuts[col.name] = np.ceil(
                    np.histogram_bin_edges(np.arange(col.minimum, col.maximum + 1)),
                    casting="unsafe",
                    dtype=np.int64,
                ).tolist()
            else:
                pass
                # print(f"Column {col.name} automatic key/cuts unsupported yet.")
        return keys, cuts

    def synth(
        self,
        columns: list[str],
        keys: dict | None = None,
        cuts: dict | None = None,
        epsilon: float | None = None,
        delta: float | None = None,
        rho: float | None = None,
        approx_zcdp: bool = True,
    ) -> QueryResponse:
        opendp_pipeline = pl.LazyFrame().select(columns)

        body_json = self._get_opendp_request_body(
            opendp_pipeline,
            epsilon=epsilon,
            delta=delta,
            rho=rho,
            approx_zcdp=approx_zcdp,
        )
        computed_keys, computed_cuts = self._gen_key_cuts()

        body_json["columns"] = columns
        body_json["keys"] = {col: v for col, v in computed_keys.items() if col in columns}
        if keys is not None:
            body_json["keys"] |= keys

        body_json["cuts"] = {col: v for col, v in computed_cuts.items() if col in columns}
        if cuts is not None:
            body_json["cuts"] |= cuts

        residual = set(columns) ^ (set(body_json["keys"]) | set(body_json["cuts"]))
        if len(residual) > 0:
            print(f"dropping {residual} columns, not keys/cuts automatically generated of specified")
            body_json["columns"] = list(set(columns) - residual)

        body = OpenDPSynthDataQueryModel.model_validate(body_json)
        res = self.http_client.post("opendp_synth_query", body)

        return validate_model_response(self.http_client, res, QueryResponse)

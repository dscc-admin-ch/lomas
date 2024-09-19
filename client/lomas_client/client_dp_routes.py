import base64
import json
import pickle
from typing import List, Optional

import opendp as dp
import pandas as pd
from diffprivlib_logger import serialise_pipeline
from fastapi import status
from sklearn.pipeline import Pipeline
from smartnoise_synth_logger import serialise_constraints

from lomas_client.client import Client
from lomas_client.constants import (
    DIFFPRIVLIB_READ_TIMEOUT,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    SMARTNOISE_SYNTH_READ_TIMEOUT,
    SNSYNTH_DEFAULT_SAMPLES_NB,
)
from lomas_client.utils import raise_error, validate_synthesizer


class DPClient(Client):
    """Client for DP Libraries related queries"""

    def smartnoise_sql_query(
        self,
        query: str,
        epsilon: float,
        delta: float,
        mechanisms: dict[str, str] = {},
        postprocess: bool = True,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[dict]:
        """This function executes a SmartNoise SQL query.

        Args:
            query (str): The SQL query to execute.
                NOTE: the table name is df, the query must end with “FROM df”.
            epsilon (float): Privacy parameter (e.g., 0.1).
            delta (float): Privacy parameter (e.g., 1e-5).
            mechanisms (dict[str, str], optional): Dictionary of mechanisms for the\
                query `See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#overriding-mechanisms>`__

                Defaults to {}.
            postprocess (bool, optional): Whether to postprocess the query results.\
                `See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__

                Defaults to True.
            dummy (bool, optional): Whether to use a dummy dataset.

                Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.

                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.

                Defaults to DUMMY_SEED.

        Returns:
            Optional[dict]: A Pandas DataFrame containing the query results.
        """
        body_json = {
            "query_str": query,
            "dataset_name": self.dataset_name,
            "epsilon": epsilon,
            "delta": delta,
            "mechanisms": mechanisms,
            "postprocess": postprocess,
        }
        if dummy:
            endpoint = "dummy_smartnoise_sql_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "smartnoise_sql_query"

        res = self._exec(endpoint, body_json)

        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            response_dict = json.loads(data)
            response_dict["query_response"] = pd.DataFrame.from_dict(
                response_dict["query_response"], orient="tight"
            )
            return response_dict

        raise_error(res)
        return None

    def estimate_smartnoise_sql_cost(
        self,
        query: str,
        epsilon: float,
        delta: float,
        mechanisms: dict[str, str] = {},
    ) -> Optional[dict[str, float]]:
        """This function estimates the cost of executing a SmartNoise query.

        Args:
            query (str): The SQL query to estimate the cost for. NOTE: the table name \
                is df, the query must end with “FROM df”.
            epsilon (float): Privacy parameter (e.g., 0.1).
            delta (float): Privacy parameter (e.g., 1e-5).
                mechanisms (dict[str, str], optional): Dictionary of mechanisms for the\
                query `See Smartnoise-SQL postprocessing documentation.
                <https://docs.smartnoise.org/sql/advanced.html#postprocess>`__
                Defaults to {}.

        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        body_json = {
            "query_str": query,
            "dataset_name": self.dataset_name,
            "epsilon": epsilon,
            "delta": delta,
            "mechanisms": mechanisms,
        }
        res = self._exec("estimate_smartnoise_sql_cost", body_json)

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))
        raise_error(res)
        return None

    def smartnoise_synth_query(
        self,
        synth_name: str,
        epsilon: float,
        delta: Optional[float] = None,
        select_cols: List[str] = [],
        synth_params: dict = {},
        nullable: bool = True,
        constraints: dict = {},
        dummy: bool = False,
        return_model: bool = False,
        condition: str = "",
        nb_samples: int = SNSYNTH_DEFAULT_SAMPLES_NB,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[dict]:
        """This function executes a SmartNoise Synthetic query.

        Args:
            synth_name (str): name of the Synthesizer model to use.
                Available synthesizer are
                    - "aim",
                    - "mwem",
                    - "dpctgan" with `disabled_dp` always forced to False and a
                    warning due to not cryptographically secure random generator
                    - "patectgan"
                    - "dpgan" with a warning due to not cryptographically secure
                    random generator
                Available under certain conditions:
                    - "mst" if `return_model=False`
                    - "pategan" if the dataset has enough rows
                Not available:
                    - "pacsynth" due to Rust panic error
                    - "quail" currently unavailable in Smartnoise Synth
                For further documentation on models, please see here:
                https://docs.smartnoise.org/synth/index.html#synthesizers-reference
            epsilon (float): Privacy parameter (e.g., 0.1).
            delta (float): Privacy parameter (e.g., 1e-5).
            select_cols (List[str]): List of columns to select.
                Defaults to None.
            synth_params (dict): Keyword arguments to pass to the synthesizer
                constructor.
                See https://docs.smartnoise.org/synth/synthesizers/index.html#, provide
                all parameters of the model except `epsilon` and `delta`.
                Defaults to None.
            nullable (bool): True if some data cells may be null
                Defaults to True.
            constraints: Dictionnary for custom table transformer constraints.
                Column that are not specified will be inferred based on metadata.
                Defaults to {}.
                For further documentation on constraints, please see here:
                https://docs.smartnoise.org/synth/transforms/index.html.
                Note: lambda function in `AnonimizationTransformer` are not supported.
            return_model (bool): True to get Synthesizer model, False to get samples
                Defaults to False
            condition (Optional[str]): sampling condition in `model.sample`
                (only relevant if return_model is False)
                Defaults to "".
            nb_samples (Optional[int]): number of samples to generate.
                (only relevant if return_model is False)
                Defaults to SNSYNTH_DEFAULT_SAMPLES_NB
            dummy (bool, optional): Whether to use a dummy dataset.
                Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.
                Defaults to DUMMY_SEED.
        Returns:
            Optional[dict]: A Pandas DataFrame containing the query results.
        """
        validate_synthesizer(synth_name, return_model)
        constraints = serialise_constraints(constraints) if constraints else ""

        body_json = {
            "dataset_name": self.dataset_name,
            "synth_name": synth_name,
            "epsilon": epsilon,
            "delta": delta,
            "select_cols": select_cols,
            "synth_params": synth_params,
            "nullable": nullable,
            "constraints": constraints,
            "return_model": return_model,
            "condition": condition,
            "nb_samples": nb_samples,
        }
        if dummy:
            endpoint = "dummy_smartnoise_synth_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "smartnoise_synth_query"

        res = self._exec(
            endpoint, body_json, read_timeout=SMARTNOISE_SYNTH_READ_TIMEOUT
        )

        if res.status_code == status.HTTP_200_OK:
            response = res.json()
            query_response = response["query_response"]
            if return_model:
                model = base64.b64decode(query_response)
                response["query_response"] = pickle.loads(model)
            else:
                response["query_response"] = pd.DataFrame(query_response)
            return response

        raise_error(res)
        return None

    def estimate_smartnoise_synth_cost(
        self,
        synth_name: str,
        epsilon: float,
        delta: Optional[float] = None,
        select_cols: List[str] = [],
        synth_params: dict = {},
        nullable: bool = True,
        constraints: dict = {},
    ) -> Optional[dict[str, float]]:
        """This function estimates the cost of executing a SmartNoise query.

        Args:
            synth_name (str): name of the Synthesizer model to use.
                Available synthesizer are
                    - "aim",
                    - "mwem",
                    - "dpctgan" with `disabled_dp` always forced to False and a
                    warning due to not cryptographically secure random generator
                    - "patectgan"
                    - "dpgan" with a warning due to not cryptographically secure
                    random generator
                Available under certain conditions:
                    - "mst" if `return_model=False`
                    - "pategan" if the dataset has enough rows
                Not available:
                    - "pacsynth" due to Rust panic error
                    - "quail" currently unavailable in Smartnoise Synth
                For further documentation on models, please see here:
                https://docs.smartnoise.org/synth/index.html#synthesizers-reference
            epsilon (float): Privacy parameter (e.g., 0.1).
            delta (float): Privacy parameter (e.g., 1e-5).
            select_cols (List[str]): List of columns to select.
                Defaults to None.
            synth_params (dict): Keyword arguments to pass to the synthesizer
                constructor.
                See https://docs.smartnoise.org/synth/synthesizers/index.html#, provide
                all parameters of the model except `epsilon` and `delta`.
                Defaults to None.
            nullable (bool): True if some data cells may be null
                Defaults to True.
            constraints (dict): Dictionnary for custom table transformer constraints.
                Column that are not specified will be inferred based on metadata.
                Defaults to {}.
                For further documentation on constraints, please see here:
                https://docs.smartnoise.org/synth/transforms/index.html.
                Note: lambda function in `AnonimizationTransformer` are not supported.
        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        validate_synthesizer(synth_name)
        constraints = serialise_constraints(constraints) if constraints else ""

        body_json = {
            "dataset_name": self.dataset_name,
            "synth_name": synth_name,
            "epsilon": epsilon,
            "delta": delta,
            "select_cols": select_cols,
            "synth_params": synth_params,
            "nullable": nullable,
            "constraints": constraints,
        }
        res = self._exec(
            "estimate_smartnoise_synth_cost",
            body_json,
            read_timeout=SMARTNOISE_SYNTH_READ_TIMEOUT,
        )

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))
        raise_error(res)
        return None

    def opendp_query(
        self,
        opendp_pipeline: dp.Measurement,
        fixed_delta: Optional[float] = None,
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Optional[dict]:
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
        body_json = {
            "dataset_name": self.dataset_name,
            "opendp_json": opendp_json,
            "fixed_delta": fixed_delta,
        }
        if dummy:
            endpoint = "dummy_opendp_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "opendp_query"

        res = self._exec(endpoint, body_json)
        if res.status_code == status.HTTP_200_OK:
            data = res.content.decode("utf8")
            response_dict = json.loads(data)
            return response_dict

        raise_error(res)
        return None

    def estimate_opendp_cost(
        self,
        opendp_pipeline: dp.Measurement,
        fixed_delta: Optional[float] = None,
    ) -> Optional[dict[str, float]]:
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
        body_json = {
            "dataset_name": self.dataset_name,
            "opendp_json": opendp_json,
            "fixed_delta": fixed_delta,
        }
        res = self._exec("estimate_opendp_cost", body_json)

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))

        raise_error(res)
        return None

    def diffprivlib_query(
        self,
        pipeline: Pipeline,
        feature_columns: List[str],
        target_columns: Optional[List[str]] = None,
        test_size: float = 0.2,
        test_train_split_seed: int = 1,
        imputer_strategy: str = "drop",
        dummy: bool = False,
        nb_rows: int = DUMMY_NB_ROWS,
        seed: int = DUMMY_SEED,
    ) -> Pipeline:
        """This function trains a DiffPrivLib pipeline on the sensitive data
        and return a trained Pipeline.

        Args:
            pipeline (sklearn.pipeline): DiffPrivLib pipeline with three conditions:
                - The pipeline MUST start with a `models.StandardScaler`.
                  Otherwise a PrivacyLeakWarning is raised by DiffPrivLib library and
                  is treated as an error in lomas server.
                - `random_state` fields can only be int (`RandomState` will not work).
                - `accountant` fields must be None.
                Note: as in DiffPrivLib, avoid any DiffprivlibCompatibilityWarning
                to ensure that the pipeline does what is intended.
            feature_columns (list[str]): the list of feature column to train
            target_columns (list[str], optional): the list of target column to predict \
                May be None for certain models.
            test_size (float, optional): proportion of the test set \
                Defaults to 0.2.
            test_train_split_seed (int, optional): seed for random train test split \
                Defaults to 1.
            imputer_strategy (str, optional): imputation strategy. Defaults to "drop".
                "drop": will drop all rows with missing values
                "mean": will replace values by the mean of the column values
                "median": will replace values by the median of the column values
                "most_frequent": : will replace values by the most frequent values
            dummy (bool, optional): Whether to use a dummy dataset. Defaults to False.
            nb_rows (int, optional): The number of rows in the dummy dataset.\
                Defaults to DUMMY_NB_ROWS.
            seed (int, optional): The random seed for generating the dummy dataset.\
                Defaults to DUMMY_SEED.

        Returns:
            Optional[Pipeline]: A trained DiffPrivLip pipeline
        """
        body_json = {
            "dataset_name": self.dataset_name,
            "diffprivlib_json": serialise_pipeline(pipeline),
            "feature_columns": feature_columns,
            "target_columns": target_columns,
            "test_size": test_size,
            "test_train_split_seed": test_train_split_seed,
            "imputer_strategy": imputer_strategy,
        }
        if dummy:
            endpoint = "dummy_diffprivlib_query"
            body_json["dummy_nb_rows"] = nb_rows
            body_json["dummy_seed"] = seed
        else:
            endpoint = "diffprivlib_query"

        res = self._exec(endpoint, body_json, read_timeout=DIFFPRIVLIB_READ_TIMEOUT)
        if res.status_code == status.HTTP_200_OK:
            response = res.json()
            model = base64.b64decode(response["query_response"]["model"])
            response["query_response"]["model"] = pickle.loads(model)
            return response
        print(
            f"Error while processing DiffPrivLib request in server \
                status code: {res.status_code} message: {res.text}"
        )
        return res.text

    def estimate_diffprivlib_cost(
        self,
        pipeline: Pipeline,
        feature_columns: List[str] = [""],
        target_columns: List[str] = [""],
        test_size: float = 0.2,
        test_train_split_seed: int = 1,
        imputer_strategy: str = "drop",
    ) -> dict:
        """This function estimates the cost of executing a DiffPrivLib query.

        Args:
            pipeline (sklearn.pipeline): DiffPrivLib pipeline with three conditions:
                - The pipeline MUST start with a `models.StandardScaler`.
                  Otherwise a PrivacyLeakWarning is raised by DiffPrivLib library and
                  is treated as an error in lomas server.
                - `random_state` fields can only be int (`RandomState` will not work).
                - `accountant` fields must be None.
                Note: as in DiffPrivLib, avoid any DiffprivlibCompatibilityWarning
                to ensure that the pipeline does what is intended.
            feature_columns (list[str]): the list of feature column to train
            target_columns (list[str], optional): the list of target column to predict \
                May be None for certain models.
            test_size (float, optional): proportion of the test set \
                Defaults to 0.2.
            test_train_split_seed (int, optional): seed for random train test split \
                Defaults to 1.
            imputer_strategy (str, optional): imputation strategy. Defaults to "drop".
                "drop": will drop all rows with missing values
                "mean": will replace values by the mean of the column values
                "median": will replace values by the median of the column values
                "most_frequent": : will replace values by the most frequent values

        Returns:
            Optional[dict[str, float]]: A dictionary containing the estimated cost.
        """
        body_json = {
            "dataset_name": self.dataset_name,
            "diffprivlib_json": serialise_pipeline(pipeline),
            "feature_columns": feature_columns,
            "target_columns": target_columns,
            "test_size": test_size,
            "test_train_split_seed": test_train_split_seed,
            "imputer_strategy": imputer_strategy,
        }
        res = self._exec(
            "estimate_diffprivlib_cost",
            body_json,
            read_timeout=DIFFPRIVLIB_READ_TIMEOUT,
        )

        if res.status_code == status.HTTP_200_OK:
            return json.loads(res.content.decode("utf8"))
        print(
            f"Error while executing provided query in server:\n"
            f"status code: {res.status_code} message: {res.text}"
        )
        return res.text

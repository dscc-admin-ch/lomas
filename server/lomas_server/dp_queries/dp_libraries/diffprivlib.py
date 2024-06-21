import base64
import json
import pickle
import warnings
from typing import Dict

import diffprivlib
import pandas as pd
from diffprivlib.utils import (
    DiffprivlibCompatibilityWarning,
    PrivacyLeakWarning,
)
from fastapi import HTTPException
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from constants import NUMERICAL_DTYPES
from dp_queries.dp_querier import DPQuerier
from private_dataset.private_dataset import PrivateDataset
from utils.loggr import LOG

# DiffPrivLib warnings will trigger error
warnings.simplefilter("error", PrivacyLeakWarning)
warnings.simplefilter("error", DiffprivlibCompatibilityWarning)


class DiffPrivLibQuerier(DPQuerier):
    def __init__(
        self,
        private_dataset: PrivateDataset,
    ) -> None:
        super().__init__(private_dataset)

    def deserialise_pipeline(self, pipeline):
        try:
            dpl_pipeline = deserialise_diffprivlib_pipeline(pipeline)
        except ValueError as e:
            raise HTTPException(400, str(e))
        except Exception as exc:
            LOG.error(exc)
            raise exc
        return dpl_pipeline

    def prepare_data(self, query_json):
        data = self.private_dataset.get_pandas_df()

        imputer_strategy = query_json.imputer_strategy
        if imputer_strategy == "drop":
            data = data.dropna()
        elif imputer_strategy in ["mean", "median"]:
            numerical_cols = data.select_dtypes(
                include=NUMERICAL_DTYPES
            ).columns.tolist()
            categorical_cols = [
                col for col in data.columns if col not in numerical_cols
            ]

            # Impute numerical features using given strategy
            imp_mean = SimpleImputer(strategy=imputer_strategy)
            df_num_imputed = imp_mean.fit_transform(data[numerical_cols])

            # Impute categorical features with most frequent value
            imp_most_frequent = SimpleImputer(strategy="most_frequent")
            df_cat_imputed = imp_most_frequent.fit_transform(
                data[categorical_cols]
            )

            # Combine imputed dataframes
            data = pd.concat(
                [
                    pd.DataFrame(df_num_imputed, columns=numerical_cols),
                    pd.DataFrame(df_cat_imputed, columns=categorical_cols),
                ],
                axis=1,
            )
        elif imputer_strategy == "most_frequent":
            # Impute all features with most frequent value
            imp_most_frequent = SimpleImputer(strategy=imputer_strategy)
            data = pd.DataFrame(
                imp_most_frequent.fit_transform(data), columns=data.columns
            )
        else:
            raise HTTPException(
                500, f"Imputation strategy {imputer_strategy} not supported"
            )

        feature_data = data[query_json.feature_columns]

        if query_json.target_columns is None:
            x_train, x_test = train_test_split(
                feature_data,
                test_size=query_json.test_size,
                random_state=query_json.test_train_split_seed,
            )
            y_train, y_test = None, None
        else:
            label_data = data[query_json.target_columns]
            x_train, x_test, y_train, y_test = train_test_split(
                feature_data,
                label_data,
                test_size=query_json.test_size,
                random_state=query_json.test_train_split_seed,
            )
        return x_train, x_test, y_train, y_test

    def fit_pipeline(self, pipeline, x_train, y_train):
        try:
            pipeline.fit(x_train, y_train)
        except Exception as e:
            LOG.exception(f"Cannot train model error: {str(e)}")
            raise HTTPException(500, f"Cannot train model error: {str(e)}")
        return pipeline

    def cost(self, query_json: dict) -> tuple[float, float]:
        dpl_pipeline = self.deserialise_pipeline(query_json.diffprivlib_json)
        x_train, _, y_train, _ = self.prepare_data(query_json)
        fitted_dpl_pipeline = self.fit_pipeline(dpl_pipeline, x_train, y_train)

        # Compute budget
        spent_epsilon = 0.0
        spent_delta = 0.0
        for step in fitted_dpl_pipeline.steps:
            spent_epsilon += step[1].accountant.spent_budget[0][0]
            spent_delta += step[1].accountant.spent_budget[0][1]
        return spent_epsilon, spent_delta

    def query(self, query_json: dict) -> Dict:
        dpl_pipeline = self.deserialise_pipeline(query_json.diffprivlib_json)
        x_train, x_test, y_train, y_test = self.prepare_data(query_json)
        fitted_dpl_pipeline = self.fit_pipeline(dpl_pipeline, x_train, y_train)

        # Model accuracy
        score = fitted_dpl_pipeline.score(x_test, y_test)

        # Serialise model
        pickled_model = base64.b64encode(
            pickle.dumps(fitted_dpl_pipeline)
        ).decode("utf-8")

        query_response = {"score": score, "model": pickled_model}
        return query_response


class DiffPrivLibDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(
            self, object_hook=self.object_hook, *args, **kwargs
        )

    def object_hook(self, dct):
        if "_tuple" in dct.keys():
            return tuple(dct["_items"])

        for k, v in dct.items():
            if type(v) is str:
                if v[:10] == "_dpl_type:":
                    try:
                        dct[k] = getattr(diffprivlib.models, v[10:])
                    except Exception as e:
                        LOG.exception(e)

                elif v[:14] == "_dpl_instance:":
                    try:
                        dct[k] = getattr(diffprivlib, v[14:])()
                    except Exception as e:
                        LOG.exception(e)

        return dct


def deserialise_diffprivlib_pipeline(diffprivlib_json):
    dct = json.loads(diffprivlib_json, cls=DiffPrivLibDecoder)
    if "module" in dct.keys():
        if dct["module"] != "diffprivlib":
            raise ValueError("JSON 'module' not equal to 'diffprivlib'")
    else:
        raise ValueError("Key 'module' not in submitted json request.")

    if "version" in dct.keys():
        if dct["version"] != diffprivlib.__version__:
            raise ValueError(
                f"Requested version does not match available version:"
                f" {diffprivlib.__version__}."
            )
    else:
        raise ValueError("Key 'version' not in submitted json request.")

    return Pipeline(
        [
            (val["name"], val["type"](**val["params"]))
            for val in dct["pipeline"]
        ]
    )

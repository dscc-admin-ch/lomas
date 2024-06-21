import json

import diffprivlib
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from constants import NUMERICAL_DTYPES
from utils.error_handler import InternalServerException
from utils.loggr import LOG


def impute_missing_data(data, imputer_strategy: str) -> pd.DataFrame:

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
        raise InternalServerException(
            f"Imputation strategy {imputer_strategy} not supported."
        )
    return data


def split_train_test_data(data, query_json):
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


class DiffPrivLibDecoder(json.JSONDecoder):
    """Decoder for DiffprivLib pipeline from str to model"""

    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(
            self, object_hook=self.object_hook, *args, **kwargs
        )

    def object_hook(self, dct):
        if "_tuple" in dct.keys():
            return tuple(dct["_items"])

        for k, v in dct.items():
            if isinstance(v, str):
                if v[:10] == "_dpl_type:":
                    try:
                        dct[k] = getattr(diffprivlib.models, v[10:])
                    except Exception as e:
                        LOG.exception(e)
                        raise InternalServerException(e) from e

                elif v[:14] == "_dpl_instance:":
                    try:
                        dct[k] = getattr(diffprivlib, v[14:])()
                    except Exception as e:
                        LOG.exception(e)
                        raise InternalServerException(e) from e

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

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split

from constants import NUMERICAL_DTYPES
from utils.error_handler import InvalidQueryException
from utils.input_models import DiffPrivLibModel


def handle_missing_data(
    df: pd.DataFrame, imputer_strategy: str
) -> pd.DataFrame:
    """Impute missing data based on given imputation strategy for NaNs
    Args:
        df (pd.DataFrame): dataframe with the data
        imputer_strategy (str): string to indicate imputatation for NaNs
            "drop": will drop all rows with missing values
            "mean": will replace values by the mean of the column values
            "median": will replace values by the median of the column values
            "most_frequent": : will replace values by the most frequent values

    Raises:
        InvalidQueryException: If the "imputer_strategy" does not exist

    Returns:
        df (pd.DataFrame): dataframe with the imputed data
    """
    dtypes = df.dtypes

    if imputer_strategy == "drop":
        df = df.dropna()
    elif imputer_strategy in ["mean", "median"]:
        numerical_cols = df.select_dtypes(
            include=NUMERICAL_DTYPES
        ).columns.tolist()
        categorical_cols = [
            col for col in df.columns if col not in numerical_cols
        ]

        # Impute numerical features using given strategy
        imp_mean = SimpleImputer(strategy=imputer_strategy)
        df_num_imputed = imp_mean.fit_transform(df[numerical_cols])

        # Impute categorical features with most frequent value
        imp_most_frequent = SimpleImputer(strategy="most_frequent")
        df[categorical_cols] = df[categorical_cols].astype("object")
        df[categorical_cols] = df[categorical_cols].replace({pd.NA: np.nan})
        df_cat_imputed = imp_most_frequent.fit_transform(df[categorical_cols])

        # Combine imputed dataframes
        df = pd.concat(
            [
                pd.DataFrame(df_num_imputed, columns=numerical_cols),
                pd.DataFrame(df_cat_imputed, columns=categorical_cols),
            ],
            axis=1,
        )
    elif imputer_strategy == "most_frequent":
        # Impute all features with most frequent value
        imp_most_frequent = SimpleImputer(strategy=imputer_strategy)
        df[df.columns] = df[df.columns].astype("object")
        df[df.columns] = df[df.columns].replace({pd.NA: np.nan})
        df = pd.DataFrame(
            imp_most_frequent.fit_transform(df), columns=df.columns
        )
    else:
        raise InvalidQueryException(
            f"Imputation strategy {imputer_strategy} not supported."
        )

    df = df.astype(dtype=dtypes)
    return df


def split_train_test_data(
    df: pd.DataFrame, query_json: DiffPrivLibModel
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split the data between train and test set
    Args:
        df (pd.DataFrame): dataframe with the data
        query_json (DiffPrivLibModel): user input query indication
            feature_columns (list[str]): columns from data to use as features
            target_columns (list[str]): columns from data to use as target (to predict)
            test_size (float): proportion of data in the test set
            test_train_split_seed (int): seed for the random train-test split

    Returns:
        x_train (pd.DataFrame): training data features
        x_test (pd.DataFrame): testing data features
        y_train (pd.DataFrame): training data target
        y_test (pd.DataFrame): testing data target
    """
    feature_data = df[query_json.feature_columns]

    if query_json.target_columns is None:
        x_train, x_test = train_test_split(
            feature_data,
            test_size=query_json.test_size,
            random_state=query_json.test_train_split_seed,
        )
        y_train, y_test = None, None
    else:
        label_data = df[query_json.target_columns]
        x_train, x_test, y_train, y_test = train_test_split(
            feature_data,
            label_data,
            test_size=query_json.test_size,
            random_state=query_json.test_train_split_seed,
        )
    return x_train, x_test, y_train, y_test

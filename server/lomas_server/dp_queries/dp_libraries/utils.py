import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer

from lomas_core.error_handler import InvalidQueryException
from lomas_server.constants import NUMERICAL_DTYPES


def handle_missing_data(df: pd.DataFrame, imputer_strategy: str) -> pd.DataFrame:
    """Impute missing data based on given imputation strategy for NaNs.

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

    numerical_cols = df.select_dtypes(include=NUMERICAL_DTYPES).columns.tolist()
    categorical_cols = list(set(df.columns) - set(numerical_cols))

    match imputer_strategy:
        case "drop":
            df = df.dropna()
        case "mean" | "median":
            # Impute numerical features using given strategy
            imp_mean = SimpleImputer(strategy=imputer_strategy)
            df_num_imputed = imp_mean.fit_transform(df[numerical_cols])

            # Impute categorical features with most frequent value
            imp_most_frequent = SimpleImputer(strategy="most_frequent")
            df.loc[:, categorical_cols] = df[categorical_cols].astype("object").replace({pd.NA: np.nan})
            df[df.select_dtypes(bool).columns] = df.select_dtypes(bool).astype("boolean")
            df_cat_imputed = imp_most_frequent.fit_transform(df[categorical_cols]) if categorical_cols else []

            # Combine imputed dataframes
            df = pd.concat(
                [
                    pd.DataFrame(df_num_imputed, columns=numerical_cols),
                    pd.DataFrame(df_cat_imputed, columns=categorical_cols),
                ],
                axis=1,
            )
        case "most_frequent":
            # Impute all features with most frequent value
            imp_most_frequent = SimpleImputer(strategy=imputer_strategy)
            df.loc[:, categorical_cols] = df[categorical_cols].astype("object").replace({pd.NA: np.nan})
            df = pd.DataFrame(imp_most_frequent.fit_transform(df), columns=df.columns)
        case _:
            raise InvalidQueryException(f"Imputation strategy {imputer_strategy} not supported.")

    # Force int and bool type on int and bool columns
    for col in df.columns:
        if pd.api.types.is_integer_dtype(dtypes[col]) or pd.api.types.is_bool_dtype(dtypes[col]):
            df[col] = df[col].round().astype(dtypes[col])

    df = df.astype(dtype=dtypes)

    if df.shape[0] == 0:
        raise InvalidQueryException("Empty dataframe, please try another imputation strategy.")
    return df

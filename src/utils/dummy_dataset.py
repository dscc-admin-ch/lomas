import datetime
import numpy as np
import pandas as pd
import random


# Dummy datasets constants
NB_ROWS = 100
SSQL_METADATA_OPTIONS = [
    "max_ids",
    "row_privacy",
    "sample_max_ids",
    "censor_dims",
    "clamp_counts",
    "clamp_columns",
    "use_dpsu",
]
DEFAULT_NUMERICAL_MIN = -10000
DEFAULT_NUMERICAL_MAX = 10000
RANDOM_STRINGS = ["a", "b", "c", "d"]
RANDOM_DATE_START = "01/01/2000"
RANDOM_DATE_RANGE = 50 * 365 * 24 * 60 * 60  # 50 years
NB_RANDOM_NONE = 5  # if nullable, how many random none to add


def make_dummy_dataset(
    metadata: dict, schema_name: str, table_name: str
) -> pd.DataFrame:
    """
    Create a dummy dataset based on a metadata dictionnary
    Parameters:
        - metadata: dictionnary of the metadata of the real dataset
        - schema_name: name of the schema
        - table_name: name of the table
    Return:
        - df: dummy dataframe based on metatada
    """
    df = pd.DataFrame()
    for col_name, data in metadata[""][schema_name][table_name].items():
        if col_name in SSQL_METADATA_OPTIONS:
            continue

        # Create a column based on the data type
        col_type = data["type"]

        if col_type == "string":
            serie = pd.Series(random.choices(RANDOM_STRINGS, k=NB_ROWS))
        elif col_type == "boolean":
            serie = pd.Series(random.choices([True, False], k=NB_ROWS))
        elif col_type in ["int", "float"]:
            column_min = (
                data["lower"]
                if "lower" in data.keys()
                else DEFAULT_NUMERICAL_MIN
            )
            column_max = (
                data["upper"]
                if "upper" in data.keys()
                else DEFAULT_NUMERICAL_MAX
            )
            if col_type == "int":
                serie = np.random.randint(column_min, column_max, size=NB_ROWS)
            else:
                serie = np.random.uniform(column_min, column_max, size=NB_ROWS)
        elif (
            col_type == "datetime"
        ):  # From srat date and random on a range above
            start = datetime.strptime(RANDOM_DATE_START, "%m/%d/%Y")
            serie = [
                start
                + datetime.timedelta(
                    seconds=random.randrange(RANDOM_DATE_RANGE)
                )
                for _ in range(NB_ROWS)
            ]
        elif (
            col_type == "unknown"
        ):  # unknown column are ignored by snartnoise sql
            continue
        else:
            raise ValueError(
                f"unknown column type in metadata: \
                {col_type} in column {col_name}"
            )

        nullable = data["nullable"] if "nullable" in data.keys() else False

        if nullable:
            for x in range(0, NB_RANDOM_NONE):
                serie.insert(random.randrange(0, len(serie) - 1), None)
            serie = serie[:-NB_RANDOM_NONE]

        df[col_name] = serie

    return df

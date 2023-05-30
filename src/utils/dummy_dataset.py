import datetime
import numpy as np
import pandas as pd
import random

from utils.constants import DEFAULT_NUMERICAL_MAX, DEFAULT_NUMERICAL_MIN, DUMMY_NB_ROWS, DUMMY_SEED, NB_RANDOM_NONE, RANDOM_DATE_RANGE, RANDOM_DATE_START, RANDOM_STRINGS, SSQL_METADATA_OPTIONS


def make_dummy_dataset(
    metadata: dict, nb_rows: int = DUMMY_NB_ROWS, seed: int = DUMMY_SEED
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
    # Setting seed
    random.seed(seed)
    np.random.seed(seed)
    
    # Create dataframe
    df = pd.DataFrame()
    for col_name, data in metadata[""]["Schema"]["Table"].items():
        if col_name in SSQL_METADATA_OPTIONS:
            continue

        # Create a random serie based on the data type
        col_type = data["type"]

        if col_type == "string":
            serie = pd.Series(random.choices(RANDOM_STRINGS, k=nb_rows))
        elif col_type == "boolean":
            serie = pd.Series(random.choices([True, False], k=nb_rows))
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
                serie = np.random.randint(column_min, column_max, size=nb_rows)
            else:
                serie = np.random.uniform(column_min, column_max, size=nb_rows)
        elif col_type == "datetime":
            # From start date and random on a range above
            start = datetime.strptime(RANDOM_DATE_START, "%m/%d/%Y")
            serie = [
                start
                + datetime.timedelta(
                    seconds=random.randrange(RANDOM_DATE_RANGE)
                )
                for _ in range(nb_rows)
            ]
        elif col_type == "unknown":
            # Unknown column are ignored by snartnoise sql
            continue
        else:
            raise ValueError(
                f"unknown column type in metadata: \
                {col_type} in column {col_name}"
            )

        # Add None value if the column is nullable
        nullable = data["nullable"] if "nullable" in data.keys() else False

        if nullable:
            for x in range(0, NB_RANDOM_NONE):
                serie.insert(random.randrange(0, len(serie) - 1), None)
            serie = serie[:-NB_RANDOM_NONE]

        # Add randomly generated data as new column of dataframe
        df[col_name] = serie

    return df

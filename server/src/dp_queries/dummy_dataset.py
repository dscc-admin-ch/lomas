import datetime
import random

import numpy as np
import pandas as pd

from admin_database.admin_database import AdminDatabase
from constants import (
    DEFAULT_NUMERICAL_MAX,
    DEFAULT_NUMERICAL_MIN,
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    NB_RANDOM_NONE,
    RANDOM_DATE_RANGE,
    RANDOM_DATE_START,
    RANDOM_STRINGS,
)
from private_dataset.in_memory_dataset import InMemoryDataset
from utils.error_handler import InternalServerException
from utils.input_models import GetDummyDataset


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
    col_metadata = metadata["columns"]
    for col_name, data in col_metadata.items():
        # Create a random serie based on the data type
        col_type = data["type"]

        if col_type == "string":
            if "cardinality" in col_metadata[col_name].keys():
                cardinality = col_metadata[col_name]["cardinality"]
                if "categories" in col_metadata[col_name].keys():
                    categories = col_metadata[col_name]["categories"]
                    serie = pd.Series(random.choices(categories, k=nb_rows))
                else:
                    serie = pd.Series(
                        random.choices(RANDOM_STRINGS[:cardinality], k=nb_rows)
                    )
            else:
                serie = pd.Series(random.choices(RANDOM_STRINGS, k=nb_rows))
        elif col_type == "boolean":
            # type boolean instead of bool will allow null values
            serie = pd.Series(
                random.choices([True, False], k=nb_rows), dtype="boolean"
            )
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
                # pd.Series to ensure consistency between different types
                serie = pd.Series(
                    np.random.randint(column_min, column_max, size=nb_rows)
                )
            else:
                serie = pd.Series(
                    np.random.uniform(column_min, column_max, size=nb_rows)
                )
        elif col_type == "datetime":
            # From start date and random on a range above
            start = datetime.datetime.strptime(RANDOM_DATE_START, "%m/%d/%Y")
            serie = pd.Series(
                [
                    start
                    + datetime.timedelta(
                        seconds=random.randrange(RANDOM_DATE_RANGE)
                    )
                    for _ in range(nb_rows)
                ]
            )
        elif col_type == "unknown":
            # Unknown column are ignored by snartnoise sql
            continue
        else:
            raise InternalServerException(
                f"unknown column type in metadata: \
                {col_type} in column {col_name}"
            )

        # Add None value if the column is nullable
        nullable = data["nullable"] if "nullable" in data.keys() else False

        if nullable:
            # Get the indexes of 'serie'
            indexes = serie.index.tolist()
            for _ in range(0, NB_RANDOM_NONE):
                index_to_insert = random.choice(indexes)
                serie.at[index_to_insert] = None

        # Add randomly generated data as new column of dataframe
        df[col_name] = serie

    return df


def get_dummy_dataset_for_query(
    admin_database: AdminDatabase, query_json: GetDummyDataset
) -> InMemoryDataset:
    # Create dummy dataset based on seed and number of rows
    ds_metadata = admin_database.get_dataset_metadata(query_json.dataset_name)
    ds_df = make_dummy_dataset(
        ds_metadata, query_json.dummy_nb_rows, query_json.dummy_seed
    )
    ds_private_dataset = InMemoryDataset(ds_metadata, ds_df)

    return ds_private_dataset

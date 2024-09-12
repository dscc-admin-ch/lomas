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
from data_connector.in_memory_connector import InMemoryConnector
from utils.error_handler import InternalServerException
from utils.query_models import GetDummyDataset


def make_dummy_dataset(  # pylint: disable=too-many-locals
    metadata: dict, nb_rows: int = DUMMY_NB_ROWS, seed: int = DUMMY_SEED
) -> pd.DataFrame:
    """
    Create a dummy dataset based on a metadata dictionnary

    Args:
        metadata (dict): dictionnary of the metadata of the real dataset
        nb_rows (int, optional): _description_. Defaults to DUMMY_NB_ROWS.
        seed (int, optional): _description_. Defaults to DUMMY_SEED.

    Raises:
        InternalServerException: If any unknown column type occurs.

    Returns:
        pd.DataFrame: dummy dataframe based on metadata
    """
    # pylint: disable=too-many-locals
    # Creating new random generator with fixed seed
    rng = np.random.default_rng(seed)

    # Create dataframe
    df = pd.DataFrame()
    for col_name, data in metadata["columns"].items():
        # Create a random serie based on the data type
        match data["type"]:
            case "string":
                if "cardinality" in data.keys():
                    cardinality = data["cardinality"]
                    if "categories" in data.keys():
                        categories = data["categories"]
                        serie = pd.Series(rng.choice(categories, size=nb_rows))
                    else:
                        serie = pd.Series(
                            rng.choice(
                                RANDOM_STRINGS[:cardinality], size=nb_rows
                            )
                        )
                else:
                    serie = pd.Series(rng.choice(RANDOM_STRINGS, size=nb_rows))
            case "boolean":
                # type boolean instead of bool will allow null values
                serie = pd.Series(
                    rng.choice([True, False], size=nb_rows), dtype="boolean"
                )
            case "int" | "float":
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

                dtype = f"{data['type']}{data['precision']}"

                if "cardinality" in data.keys():
                    if "categories" in data.keys():
                        categories = np.array(data["categories"], dtype=dtype)
                        serie = pd.Series(rng.choice(categories, size=nb_rows))
                    else:
                        if data["type"] == "int":
                            serie = pd.Series(
                                rng.integers(
                                    1,
                                    high=data["cardinality"],
                                    endpoint=True,
                                    size=nb_rows
                                ),
                                dtype=np.dtype(dtype)
                            )
                        else:
                            raise InternalServerException(
                                "Float column cannot be categorical."
                            )
                else:
                    if data["type"] == "int":
                        # pd.Series to ensure consistency between different types
                        serie = pd.Series(
                            rng.integers(
                                column_min,
                                high=column_max,
                                endpoint=True,
                                size=nb_rows
                            ),
                            dtype=np.dtype(dtype)
                        )
                    else:
                        serie = pd.Series(
                            column_min
                            + (column_max - column_min)
                            * rng.random(size=nb_rows, dtype=np.dtype(dtype))
                        )
            case "datetime":
                # From start date and random on a range above
                start_date = (
                    data["lower"]
                    if "lower" in data.keys()
                    else datetime.datetime.strptime(
                        RANDOM_DATE_START, "%m/%d/%Y"
                    )
                )
                end_date = (
                    data["upper"]
                    if "upper" in data.keys()
                    else datetime.datetime.strptime(
                        RANDOM_DATE_START, "%m/%d/%Y"
                    )
                    + datetime.timedelta(
                        seconds=random.randrange(RANDOM_DATE_RANGE)
                    )
                )
                serie = pd.Series(
                    np.random.choice(
                        pd.date_range(start=start_date, end=end_date),
                        size=nb_rows,
                    )
                )
            case "unknown":
                # Unknown column are ignored by smartnoise sql
                continue
            case _:
                raise InternalServerException(
                    f"unknown column type in metadata: \
                    {data['type']} in column {col_name}"
                )

        # Add None value if the column is nullable
        nullable = data["nullable"] if "nullable" in data.keys() else False

        if nullable:
            # Get the indexes of 'serie'
            indexes = serie.index.tolist()
            for _ in range(0, NB_RANDOM_NONE):
                index_to_insert = rng.choice(indexes)
                serie.at[index_to_insert] = None

        # Add randomly generated data as new column of dataframe
        df[col_name] = serie

    return df


def get_dummy_dataset_for_query(
    admin_database: AdminDatabase, query_json: GetDummyDataset
) -> InMemoryConnector:
    """Get a dummy dataset for a given query.

    Args:
        admin_database (AdminDatabase): An initialized instance
            of AdminDatabase.
        query_json (GetDummyDataset): The JSON request object for the query.


    Returns:
        InMemoryConnector: An in memory dummy dataset instance.
    """
    # Create dummy dataset based on seed and number of rows
    ds_metadata = admin_database.get_dataset_metadata(query_json.dataset_name)
    ds_df = make_dummy_dataset(
        ds_metadata, query_json.dummy_nb_rows, query_json.dummy_seed
    )
    ds_data_connector = InMemoryConnector(ds_metadata, ds_df)

    return ds_data_connector

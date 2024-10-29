import numpy as np
import pandas as pd
from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import (
    BooleanMetadata,
    CategoricalColumnMetadata,
    DatetimeMetadata,
    FloatMetadata,
    IntMetadata,
    Metadata,
    StrMetadata,
)
from lomas_core.models.requests import DummyQueryModel

from lomas_server.admin_database.admin_database import AdminDatabase
from lomas_server.constants import (
    DUMMY_NB_ROWS,
    DUMMY_SEED,
    NB_RANDOM_NONE,
    RANDOM_STRINGS,
)
from lomas_server.data_connector.in_memory_connector import InMemoryConnector


def make_dummy_dataset(  # pylint: disable=too-many-locals
    metadata: Metadata, nb_rows: int = DUMMY_NB_ROWS, seed: int = DUMMY_SEED
) -> pd.DataFrame:
    """
    Create a dummy dataset based on a metadata dictionnary.

    Args:
        metadata (Metadata): The metadata model for the real dataset.
        nb_rows (int, optional): _description_. Defaults to DUMMY_NB_ROWS.
        seed (int, optional): _description_. Defaults to DUMMY_SEED.

    Raises:
        InternalServerException: If any unknown column type occurs.

    Returns:
        pd.DataFrame: dummy dataframe based on metadata
    """
    # Creating new random generator with fixed seed
    rng = np.random.default_rng(seed)

    # Create dataframe
    df = pd.DataFrame()
    for col_name, data in metadata.columns.items():
        # Create a random serie based on the data type
        match data:
            case CategoricalColumnMetadata():
                categories = data.categories
                serie = pd.Series(rng.choice(categories, size=nb_rows))
            case StrMetadata():
                serie = pd.Series(rng.choice(RANDOM_STRINGS, size=nb_rows))
            case BooleanMetadata():
                # type boolean instead of bool will allow null values below
                serie = pd.Series(
                    rng.choice([True, False], size=nb_rows), dtype="boolean"
                )
            case IntMetadata():
                # pd.Series to ensure consistency between different types
                dtype = f"{data.type}{data.precision}"
                serie = pd.Series(
                    rng.integers(
                        data.lower,
                        high=data.upper,
                        endpoint=True,
                        size=nb_rows,
                    ),
                    dtype=np.dtype(dtype),
                )
            case FloatMetadata():
                dtype = f"{data.type}{data.precision}"
                serie = pd.Series(
                    data.lower
                    + (data.upper - data.lower)
                    * rng.random(size=nb_rows, dtype=np.dtype(dtype))
                )
            case DatetimeMetadata():
                serie = pd.Series(
                    rng.choice(
                        pd.date_range(start=data.lower, end=data.upper),
                        size=nb_rows,
                    )
                )
            case _:
                raise InternalServerException(
                    f"unknown column type in metadata: \
                    {type(data)} in column {col_name}"
                )

        # Add None value if the column is nullable
        if data.nullable:
            # Get the indexes of 'serie'
            indexes = serie.index.tolist()
            for _ in range(0, NB_RANDOM_NONE):
                index_to_insert = rng.choice(indexes)
                serie.at[index_to_insert] = None

        # Add randomly generated data as new column of dataframe
        df[col_name] = serie

    return df


def get_dummy_dataset_for_query(
    admin_database: AdminDatabase, query_json: DummyQueryModel
) -> InMemoryConnector:
    """Get a dummy dataset for a given query.

    Args:
        admin_database (AdminDatabase): An initialized instance
            of AdminDatabase.
        query_json (RequestModel): The request object for the query.

    Returns:
        InMemoryConnector: An in memory dummy dataset instance.
    """
    # Create dummy dataset based on seed and number of rows
    ds_metadata = admin_database.get_dataset_metadata(query_json.dataset_name)
    ds_df = make_dummy_dataset(
        ds_metadata,
        query_json.dummy_nb_rows,
        query_json.dummy_seed,
    )
    ds_data_connector = InMemoryConnector(ds_metadata, ds_df)

    return ds_data_connector

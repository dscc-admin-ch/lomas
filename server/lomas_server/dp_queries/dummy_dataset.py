import numpy as np
import pandas as pd
from aio_pika.patterns.rpc import Proxy

from lomas_core.error_handler import InternalServerException
from lomas_core.models.collections import (
    BooleanMetadata,
    DatetimeMetadata,
    FloatMetadata,
    IntCategoricalMetadata,
    IntMetadata,
    Metadata,
    StrCategoricalMetadata,
    StrMetadata,
)
from lomas_core.models.constants import DUMMY_NB_ROWS, DUMMY_SEED
from lomas_core.models.requests import DummyQueryModel
from lomas_server.constants import RANDOM_STRINGS
from lomas_server.data_connector.in_memory_connector import InMemoryConnector


def make_dummy_dataset(
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
            case StrCategoricalMetadata():
                categories = data.categories
                serie = pd.Series(rng.choice(categories, size=nb_rows))
            case StrMetadata():
                serie = pd.Series(rng.choice(RANDOM_STRINGS, size=nb_rows))
            case BooleanMetadata():
                # type boolean instead of bool will allow null values below
                serie = pd.Series(rng.choice([True, False], size=nb_rows), dtype="boolean")
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
            case IntCategoricalMetadata():
                dtype = f"{data.type}{data.precision}"
                int_categories = data.categories
                serie = pd.Series(rng.choice(int_categories, size=nb_rows), dtype=np.dtype(dtype))
            case FloatMetadata():
                dtype = f"{data.type}{data.precision}"
                serie = pd.Series(
                    data.lower + (data.upper - data.lower) * rng.random(size=nb_rows, dtype=np.dtype(dtype))
                )
                if data.int_with_nulls:
                    serie = serie.round(0)
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

        # Add nullable_proportion proportion of None values
        if data.nullable_proportion:
            indexes = serie.index.tolist()
            for _ in range(0, int(nb_rows * data.nullable_proportion)):
                index_to_insert = rng.choice(indexes)
                serie.loc[index_to_insert] = None

        # Add randomly generated data as new column of dataframe
        df[col_name] = serie

    return df


async def get_dummy_dataset_for_query(
    admin_database: Proxy, query_json: DummyQueryModel
) -> InMemoryConnector:
    """Get a dummy dataset for a given query.

    Args:
        admin_database (Proxy): A Proxy for an initialized instance of an AdminDatabase.
        query_json (RequestModel): The request object for the query.

    Returns:
        InMemoryConnector: An in memory dummy dataset instance.
    """
    # Create dummy dataset based on seed and number of rows
    metadata = await admin_database.get_dataset_metadata(dataset_name=query_json.dataset_name)
    df = make_dummy_dataset(
        metadata,
        query_json.dummy_nb_rows,
        query_json.dummy_seed,
    )
    return InMemoryConnector(metadata=metadata, df=df)

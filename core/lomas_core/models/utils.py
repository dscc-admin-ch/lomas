import json
import pickle
from base64 import b64decode, b64encode
from typing import Any

import pandas as pd
import polars as pl

PANDAS_SERIALIZATION_ORIENT = "tight"


def dataframe_to_dict(df: pd.DataFrame) -> dict:
    """Transforms pandas dataframe into a dictionary.

    Args:
        df (pd.DataFrame): The dataframe to "serialize".

    Returns:
        dict: The pandas dataframe in dictionary format.
    """
    return df.to_dict(orient=PANDAS_SERIALIZATION_ORIENT)


def dataframe_from_dict(serialized_df: pd.DataFrame | dict) -> pd.DataFrame:
    """Transforms input dict into pandas dataframe.

    If the input is already a dataframe, it is simply returned unmodified.

    Args:
        serialized_df (pd.DataFrame | dict): Dataframe in dict format.
            Or pd.Dataframe.

    Returns:
        pd.DataFrame: The transformed dataframe.
    """
    if isinstance(serialized_df, pd.DataFrame):
        return serialized_df

    return pd.DataFrame.from_dict(serialized_df, orient=PANDAS_SERIALIZATION_ORIENT)


def polars_df_to_str(df_pl: pl.DataFrame) -> str:
    """Convert a Polars DataFrame to a JSON string."""
    return df_pl.write_json()


def polars_df_from_str(serialized_pl: str | pl.DataFrame) -> pl.DataFrame:
    """Convert a Polars DataFrame from a JSON string."""

    if isinstance(serialized_pl, pl.DataFrame):
        return serialized_pl

    df_pl = json.loads(serialized_pl)
    return pl.DataFrame(df_pl)


def serialize_model(model: Any) -> str:
    """
    Serialise a python object into an utf-8 string.

    Fitted Smartnoise Synth synthesizer or fitted DiffPrivLib pipeline.

    Args:
        model (Any): An object to serialise

    Returns:
        str: string of serialised model
    """
    serialized = b64encode(pickle.dumps(model))
    return serialized.decode("utf-8")


def deserialize_model(serialized_model: Any) -> Any:
    """Deserialize a base64 encoded byte string into a python object.

    Args:
        serialized_model (Any): Encoded python object.

    Returns:
        Any: Deserialized python object.
    """
    if isinstance(serialized_model, str):
        raw_bytes = b64decode(serialized_model)
        return pickle.loads(raw_bytes)

    return serialized_model

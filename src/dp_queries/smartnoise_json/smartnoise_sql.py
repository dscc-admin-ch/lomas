import io
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from snsql import Privacy, from_connection
import traceback
import pandas as pd
import yaml

from dp_queries.dp_logic import DPQuerier
import globals
from utils.constants import (
    IRIS_DATASET,
    IRIS_DATASET_PATH,
    IRIS_METADATA_PATH,
    PENGUIN_DATASET,
    PENGUIN_DATASET_PATH,
    PENGUIN_METADATA_PATH,
)


def smartnoise_dataset_factory(dataset_name: str):
    if dataset_name == IRIS_DATASET:
        if globals.IRIS_QUERIER is None:
            globals.IRIS_QUERIER = SmartnoiseSQLQuerier(
                IRIS_DATASET_PATH, IRIS_METADATA_PATH
            )
        querier = globals.IRIS_QUERIER
    elif dataset_name == PENGUIN_DATASET:
        if globals.PENGUIN_QUERIER is None:
            globals.PENGUIN_QUERIER = SmartnoiseSQLQuerier(
                PENGUIN_DATASET_PATH, PENGUIN_METADATA_PATH
            )
        querier = globals.PENGUIN_QUERIER
    else:
        raise (f"Dataset {dataset_name} unknown.")

    return querier


class SmartnoiseSQLQuerier(DPQuerier):
    def __init__(self, csv_path: str, metadata_path: str) -> None:
        self.df = pd.read_csv(csv_path)

        with open(metadata_path, "r") as f:
            self.metadata = yaml.safe_load(f)

    def cost(self, query_str: str, eps: float, delta: float) -> [float, float]:
        privacy = Privacy(epsilon=eps, delta=delta)
        reader = from_connection(
            self.df, privacy=privacy, metadata=self.metadata
        )

        try:
            result = reader.get_privacy_cost(query_str)
        except Exception as err:
            print(traceback.format_exc())
            raise HTTPException(
                400,
                "Error executing query: " + query_str + ": " + str(err),
            )

        return result

    def query(self, query_str: str, eps: float, delta: float) -> list:
        privacy = Privacy(epsilon=eps, delta=delta)
        reader = from_connection(
            self.df, privacy=privacy, metadata=self.metadata
        )

        try:
            result = reader.execute(query_str)
        except Exception as err:
            raise HTTPException(
                400,
                "Error executing query: " + query_str + ": " + str(err),
            )

        # TODO: understand better (why need to stream ?)
        db_res = result.copy()
        cols = result.pop(0)

        if result == []:
            raise HTTPException(
                400,
                f"SQL Reader generated empty results, \
                    Epsilon: {eps} and Delta: {delta} are too small \
                        to generate output.",
            )
        stream = io.StringIO()
        df_res = pd.DataFrame(result, columns=cols)

        # CSV creation
        df_res.to_csv(stream, index=False)

        response = StreamingResponse(
            iter([stream.getvalue()]), media_type="text/csv"
        )
        response.headers[
            "Content-Disposition"
        ] = "attachment; filename=synthetic_data.csv"
        return (response, db_res)

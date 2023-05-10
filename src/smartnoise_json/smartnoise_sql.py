import io
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from snsql import Privacy, from_connection
import traceback
import pandas as pd
import globals

from utils.constants import (
    IRIS_DATASET_PATH,
    IRIS_METADATA_PATH,
    PENGUIN_DATASET_PATH,
    PENGUIN_METADATA_PATH
)

def smartnoise_dataset_factory(dataset_name: str):
    if dataset_name == 'Iris':
        querier = SmartnoiseSQLQuerier(IRIS_DATASET_PATH, IRIS_METADATA_PATH)
    elif dataset_name == 'Penguin':
        querier = SmartnoiseSQLQuerier(PENGUIN_DATASET_PATH, PENGUIN_METADATA_PATH)
    else:
        raise(f'Dataset {dataset_name} unknown.')


class SmartnoiseSQLQuerier:

    def __init__(self, csv_path: str, metadata_path: str):
        self.df = pd.read_csv(csv_path)

        with open(metadata_path, "r") as f:
            self.metadata = yaml.safe_load(f)

    def cost(self, query_str, eps, dta):
        privacy = Privacy(epsilon=eps, delta=dta)
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

    def query(self, query_str, eps, dta) -> list:
        privacy = Privacy(epsilon=eps, delta=dta)
        reader = from_connection(
            self.df, privacy=privacy, metadata=self.metadata
        )

        try:
            result = reader.execute(query_str)
            privacy_cost = reader.get_privacy_cost(query_str)
        except Exception as err:
            globals.LOG.exception(err)
            raise HTTPException(
                400,
                "Error executing query: " + query_str + ": " + str(err),
            )

        db_res = result.copy()
        cols = result.pop(0)

        if result == []:
            raise HTTPException(
                400,
                f"SQL Reader generated empty results, \
                    Epsilon: {eps} and Delta: {dta} are too small \
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
        return (response, privacy_cost, db_res)

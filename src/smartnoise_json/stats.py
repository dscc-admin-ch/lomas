import io
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
import snsql
from snsql import Privacy
import traceback
import pandas as pd
import globals
class DPStats():
    df: pd.DataFrame

    def __init__(self, df: pd.DataFrame):
        # create metadata 
        # assumes inputs are all catagorical - 
        # as required by the synth data models
        cols = list(df.columns.copy())
        # if "labels" not in cols:
        #     raise ValueError("Column 'labels' not present in the dataset provided")
        if cols.sort() != list(set(cols)).sort():
            raise ValueError("Column names must be unique")

        cols.remove("y_return")
        cols.remove("y_financial_help")
        cols.remove("y_financial_actions")

        iter_cols = {c: {'type':'string'} for c in cols}
        iter_cols['y_return'] = {
                    'type': 'int',
                    'nullable': False
                }
        iter_cols['y_financial_help'] = {
                    'type': 'int',
                    'nullable': False
                }
        iter_cols['y_financial_actions'] = {
                    'type': 'int',
                    'nullable': False
                }
        iter_cols['max_ids'] = 1
        iter_cols['row_privacy'] = True

        self.meta = {'engine': 'csv',
            'comp': {
                'comp': {
                    'comp': iter_cols
                    }
                }
            }

        # copy data, converting values to string to be catagorical 
        # (to be consistent with synth data)
        self.df = df.astype("str")

    def cost(self, query_str, eps, dta):
        privacy = Privacy(epsilon=eps, delta=dta)
        reader = snsql.from_connection(self.df, privacy=privacy, metadata=self.meta)

        try:
            result = reader.get_privacy_cost(query_str)
        except Exception as err:
            print(traceback.format_exc())
            raise HTTPException(400, "Error executing query: " + query_str + ": " + str(err))
            
        
        return result

    def query(self, query_str, eps, dta) -> list:
        privacy = Privacy(epsilon=eps, delta=dta)
        reader = snsql.from_connection(self.df, privacy=privacy, metadata=self.meta)

        try:
            result = reader.execute(query_str)
            privacy_cost = reader.get_privacy_cost(query_str)
        except Exception as err:
            globals.LOG.exception(err)
            raise HTTPException(400, "Error executing query: " + query_str + ": " + str(err))
        
        db_res = result.copy()
        cols = result.pop(0)

        if result == []:
            raise HTTPException(400, f"SQL Reader generated empty results, Epsilon: {eps} and Delta: {dta} are too small to generate output.")
        stream = io.StringIO()
        df_res = pd.DataFrame(result, columns=cols)
    
        # CSV creation
        df_res.to_csv(stream, index=False)

        response = StreamingResponse(
            iter([stream.getvalue()]),
            media_type="text/csv"
        )
        response.headers["Content-Disposition"] = "attachment; filename=synthetic_data.csv"
        return response, privacy_cost, db_res


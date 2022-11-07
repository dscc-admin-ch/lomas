from fastapi import HTTPException
import snsql
from snsql import Privacy
import traceback
import pandas as pd

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
                    'type': 'boolean',
                    'nullable': False
                }
        iter_cols['y_financial_help'] = {
                    'type': 'boolean',
                    'nullable': False
                }
        iter_cols['y_financial_actions'] = {
                    'type': 'boolean',
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
            print(traceback.format_exc())
            raise HTTPException(400, "Error executing query: " + query_str + ": " + str(err))
        
        return result, privacy_cost


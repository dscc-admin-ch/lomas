from dbm.ndbm import library
import time
from . import queries_coll
from .db_models import QueryEntry


#Add query to Mongo Database
def db_add_query(team_name, query, eps, dlta, res):
    entry = QueryEntry.parse_obj({
            "team_name": team_name,
            "query": query,
            "epsilon": eps,
            "delta": dlta, 
            "response": res,
            "library": library
        })
    queries_coll.insert_one(entry)

def db_get_privacy_cost(team_name:str):
    queries_history = queries_coll.find({"team_name": team_name})
    if(queries_history == None):
        return f"no entry with team name: '{team_name}'"
    return queries_history #calculate cost
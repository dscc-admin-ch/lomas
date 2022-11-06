import pandas as pd
import yaml
from pymongo import MongoClient
from loggr import LOG
import globals

#Reading runtime args for DB details
with open("/usr/runtime.yaml") as runtime:
    yam_rargs = yaml.safe_load(runtime)["runtime_args"]

try:
    ##Create a MongoDB client, open a connection to Amazon DocumentDB as a replica set and specify the read preference as secondary preferred
    client = MongoClient(f'{yam_rargs["MDDB_PROT"]}{yam_rargs["MDDB_USER"]}:{yam_rargs["MDDB_PASS"]}@{yam_rargs["MDDB_URL"]}')
    ##Specify the database to be used
    db = client[yam_rargs["MDDB_DBNAME"]]

    ##Specify the collection to be used
    queries_coll = db.request_queries
except Exception as e:
    globals.SERVER_STATE = {
         "state": "DB Client FAILED", 
         "message": str(e)
    }
    LOG.error(globals.SERVER_STATE)
    LOG.error(str(e))
    raise e


# print(list(queries_coll.find({})))
import pandas as pd
import yaml
from pymongo import MongoClient
from loggr import LOG

#Reading runtime args for DB details
with open("/usr/runtime.yaml") as runtime:
    yam_rargs = yaml.safe_load(runtime)["runtime_args"]

##Create a MongoDB client, open a connection to Amazon DocumentDB as a replica set and specify the read preference as secondary preferred
client = MongoClient(f'{yam_rargs["MDDB_PROT"]}{yam_rargs["MDDB_USER"]}:{yam_rargs["MDDB_PASS"]}@{yam_rargs["MDDB_URL"]}')

##Specify the database to be used
db = client.un_hackathon

##Specify the collection to be used
queries_coll = db.request_queries

# print(list(queries_coll.find({})))
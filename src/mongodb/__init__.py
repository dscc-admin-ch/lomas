from pymongo import MongoClient
from os import environ

connection_string = "mongodb"+("://" if not environ.get("MONGO_SRV")=="false" else "+srv://")
client_string = connection_string+environ.get("UNDB_USER")+":" + environ.get("UNDB_PASS")+"@"+environ.get("UNDB_URL")+"/?retryWrites=true&w=majority"
client = MongoClient(client_string)
##Create a MongoDB client, open a connection to Amazon DocumentDB as a replica set and specify the read preference as secondary preferred
# client = pymongo.MongoClient(f'mongodb://{DB_USER}:{DB_PASS}@stage-un-g20-nov22.cluster-clagiea8p62e.eu-west-1.docdb.amazonaws.com:27017/?tls=true&tlsCAFile=rds-combined-ca-bundle.pem&replicaSet=rs0&readPreference=secondaryPreferred&retryWrites=false')

##Specify the database to be used
db = client.un_hackathon

##Specify the collection to be used
queries_coll = db.request_queries
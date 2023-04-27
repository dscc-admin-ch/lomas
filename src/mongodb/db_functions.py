import yaml
from fastapi import HTTPException

from . import queries_coll
from .db_models import QueryDBInput, SubmissionDBInput


# Add query to Mongo Database
def db_add_query(input: QueryDBInput):
    queries_coll.update_one({"user_name": input.user_name}, {
        "$push": {
            "queries": input.query.toJSON()
        },
        "$inc": {"total_epsilon": input.query.epsilon, "total_delta": input.query.delta}
    }, upsert=True)

def db_get_budget(user_name: str):
    res = queries_coll.find_one({"user_name": user_name}, {
                                "_id": 0, "total_epsilon": 1, "total_delta": 1, })
    if (res == None or res == {}):
        raise HTTPException(400, f"no entry with user name: '{user_name}'")
    return res["total_epsilon"]


def db_get_delta(user_name: str):
    res = queries_coll.find_one({"user_name": user_name}, {
                                "_id": 0, "total_delta": 1})
    if (res == None or res == {}):
        raise HTTPException(400, f"no entry with user name: '{user_name}'")
    return res["total_delta"]


def db_add_users():
    data = {}
    with open('/usr/runtime.yaml', 'r') as f:
        data = yaml.safe_load(f)["runtime_args"]["settings"]
    for user in data['parties']:
        queries_coll.update_one({"user_name": user["user_name"]},{
        "$setOnInsert": {
            "user_name": user["user_name"],
            "queries": [],
            "total_epsilon": 0,
            "total_delta": 0,
            "country": user["country"]
        }
    },upsert=True)
    return True

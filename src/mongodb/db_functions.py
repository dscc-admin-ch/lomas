from fastapi import HTTPException

from . import queries_coll
from .db_models import QueryDBInput


# Add query to Mongo Database
def db_add_query(
    input: QueryDBInput,
):
    queries_coll.update_one(
        {"team_name": input.team_name},
        {
            "$push": {"queries": input.query.toJSON()},
            "$inc": {
                "total_epsilon": input.query.epsilon,
                "total_delta": input.query.delta,
            },
        },
        upsert=True,
    )


def db_get_budget(
    team_name: str,
):
    res = queries_coll.find_one(
        {"team_name": team_name},
        {
            "_id": 0,
            "total_epsilon": 1,
            "total_delta": 1,
        },
    )
    if res is None or res == {}:
        raise HTTPException(
            400,
            f"no entry with team name: '{team_name}'",
        )
    return res["total_epsilon"]


def db_get_delta(
    team_name: str,
):
    res = queries_coll.find_one(
        {"team_name": team_name},
        {
            "_id": 0,
            "total_delta": 1,
        },
    )
    if res is None or res == {}:
        raise HTTPException(
            400,
            f"no entry with team name: '{team_name}'",
        )
    return res["total_delta"]

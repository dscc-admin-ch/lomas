import yaml
from fastapi import (
    HTTPException,
)

from . import queries_coll
from .db_models import (
    QueryDBInput,
    SubmissionDBInput,
)


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


def db_get_accuracy(
    team_name: str,
):
    res = queries_coll.find_one(
        {"team_name": team_name},
        {
            "_id": 0,
            "accuracy": 1,
        },
    )
    if res is None or res == {}:
        raise HTTPException(
            400,
            f"no entry with team name: '{team_name}'",
        )
    return res["accuracy"]


def db_get_score(
    team_name: str,
):
    res = queries_coll.find_one(
        {"team_name": team_name},
        {
            "_id": 0,
            "score": 1,
        },
    )
    if res is None or res == {}:
        raise HTTPException(
            400,
            f"no entry with team name: '{team_name}'",
        )
    return res["score"]


def db_get_final_accuracy(
    team_name: str,
):
    res = queries_coll.find_one(
        {"team_name": team_name},
        {
            "_id": 0,
            "final_accuracy": 1,
        },
    )
    if res is None or res == {}:
        raise HTTPException(
            400,
            f"no entry with team name: '{team_name}'",
        )
    return res["final_accuracy"]


def db_get_final_score(
    team_name: str,
):
    res = queries_coll.find_one(
        {"team_name": team_name},
        {
            "_id": 0,
            "final_score": 1,
        },
    )
    if res is None or res == {}:
        raise HTTPException(
            400,
            f"no entry with team name: '{team_name}'",
        )
    return res["final_score"]


def db_add_submission(
    team_name: str,
    input: SubmissionDBInput,
):
    score = db_get_score(team_name)
    accuracy = db_get_accuracy(team_name)
    epsilon = db_get_budget(team_name)
    delta = db_get_delta(team_name)
    final_score = db_get_final_score(team_name)
    final_accuracy = db_get_final_accuracy(team_name)
    input.epsilon = epsilon
    input.delta = delta
    accuracy, score = (
        (
            input.accuracy,
            input.score,
        )
        if input.score > score
        else (accuracy, score)
    )
    (final_accuracy, final_score,) = (
        (
            input.final_accuracy,
            input.final_score,
        )
        if input.final_score > final_score
        else (
            final_accuracy,
            final_score,
        )
    )
    # score = input.score if input.score > score else score
    queries_coll.update_one(
        {"team_name": team_name},
        {
            "$push": {"submissions": input.toJSON()},
            "$set": {
                "score": score,
                "accuracy": accuracy,
                "final_accuracy": final_accuracy,
                "final_score": final_score,
            },
        },
    )


def db_add_teams():
    data = {}
    with open(
        "/usr/runtime.yaml",
        "r",
    ) as f:
        data = yaml.safe_load(f)["runtime_args"]["settings"]
    for team in data["parties"]:
        queries_coll.update_one(
            {"team_name": team["team_name"]},
            {
                "$setOnInsert": {
                    "team_name": team["team_name"],
                    "queries": [],
                    "submissions": [],
                    "total_epsilon": 0,
                    "total_delta": 0,
                    "accuracy": 0,
                    "score": 0,
                    "final_accuracy": 0,
                    "final_score": 0,
                    "all_female": team["all_female"],
                    "all_student": team["all_student"],
                    "country": team["country"],
                    "location": team["location"],
                }
            },
            upsert=True,
        )
    return True


def db_get_leaderboard():
    res = queries_coll.aggregate(
        [
            {
                "$replaceRoot": {
                    "newRoot": {
                        "name": "$team_name",
                        "delta": "$delta",
                        "epsilon": "$epsilon",
                        "accuracy": "$accuracy",  # Max accuracy of submission
                        "score": "$score",  # Max score of submission
                        "timestamp": {
                            "$ifNull": [
                                {
                                    "$arrayElemAt": [
                                        "$submissions.timestamp",
                                        -1,
                                    ]
                                },
                                0,
                            ]
                        },  # TimeStamp of last submission
                    }
                }
            },
            {"$sort": {"score": -1}},
        ]
    )
    return [x for x in res]


def db_get_last_submission(
    team_name,
):
    team = queries_coll.find_one(
        {"team_name": team_name},
        {
            "_id": 0,
            "accuracy": 1,
        },
    )

    if not team:
        return None

    res = queries_coll.aggregate(
        [
            {"$match": {"team_name": team_name}},
            {
                "$project": {
                    "timestamp": {
                        "$ifNull": [
                            {
                                "$arrayElemAt": [
                                    "$submissions.timestamp",
                                    -1,
                                ]
                            },
                            0,
                        ]
                    },
                    "_id": 0,
                }
            },
        ]
    )
    res = res.next()
    return res["timestamp"]

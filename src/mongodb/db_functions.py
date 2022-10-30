import yaml

from . import queries_coll
from .db_models import QueryDBInput, SubmissionDBInput


# Add query to Mongo Database
def db_add_query(input: QueryDBInput):
    queries_coll.update_one({"team_name": input.team_name}, {
        "$push": {
            "queries": input.query.toJSON()
        },
        "$inc": {"total_epsilon": input.query.epsilon, "total_delta": input.query.delta}
    }, upsert=True)

def db_get_budget(team_name: str):
    res = queries_coll.find_one({"team_name": team_name}, {
                                "_id": 0, "epsilon": 1})
    if (res == None):
        return f"no entry with team name: '{team_name}'"
    print(type(res))
    return res["epsilon"]


def db_get_delta(team_name: str):
    res = queries_coll.find_one({"team_name": team_name}, {
                                "_id": 0, "delta": 1})
    if (res == None):
        return f"no entry with team name: '{team_name}'"
    # print(type(res))
    return res["delta"]


def db_get_accuracy(team_name: str):
    res = queries_coll.find_one({"team_name": team_name}, {
                                "_id": 0, "accuracy": 1})
    if (res == None):
        return f"no entry with team name: '{team_name}'"
    # print(type(res))
    return res["accuracy"]


def db_get_score(team_name: str):
    res = queries_coll.find_one(
        {"team_name": team_name}, {"_id": 0, "score": 1})
    if (res == None):
        return f"no entry with team name: '{team_name}'"
    # print(type(res))
    return res["score"]

def db_add_submission(team_name: str, input: SubmissionDBInput):
    # print(input)
    score = db_get_score(team_name)
    accuracy = db_get_accuracy(team_name)
    accuracy, score = (input.accuracy, input.score) if input.score > score else (accuracy, score)
    # score = input.score if input.score > score else score
    queries_coll.update_one({"team_name": team_name}, {
        "$push": {
            "submissions": input.toJSON()
        },
        "$set": {
            "score": score,
            "accuracy": accuracy
        }
    })

def db_add_teams():
    data = {}
    with open('/usr/runtime.yaml', 'r') as f:
        data = yaml.safe_load(f, yaml.Loader)
    db_data = []
    for x in data['parties']:
        db_data.append({
            "team_name": x,
            "queries": [],
            "submissions": [],
            "epsilon": 0,
            "delta": 0,
            "accuracy": 0,
            "score": 0
        })
    queries_coll.insert_many(db_data)
    return


def db_get_leaderboard():
    res = queries_coll.aggregate([
        {"$replaceRoot":
            {"newRoot":
                {"name": "$team_name",
				 "delta": "$delta",
				 "epsilon": "$epsilon",
                 "accuracy": "$accuracy", #Max accuracy of submission
				 "score": "$score", #Max score of submission
				 "timestamp": {"$ifNull": [{"$arrayElemAt":["$submissions.timestamp",-1]}, 0]} #TimeStamp of last submission
             }
         }
	 },
    { "$sort" : { "score" : -1 } }
    ])
    return [x for x in res]

def db_get_last_submission(team_name):
    team = queries_coll.find_one({"team_name": team_name}, {
                                "_id": 0, "accuracy": 1})

    if not team:
        return None
        
    res = queries_coll.aggregate([{"$match":{"team_name": team_name}},{
        "$project":{
            "timestamp": {"$ifNull": [{"$arrayElemAt":["$submissions.timestamp",-1]}, 0]},
            "_id":0
        }
    }])
    res = res.next()
    return res["timestamp"]

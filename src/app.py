from fastapi import (Body, Depends, FastAPI, File, Header, HTTPException,
                     Request, UploadFile)
from fastapi.responses import StreamingResponse
from io import BytesIO
# LEADERBOARD, QUERIER, TRAIN, TEST, LIVE, set_TRAIN, set_TEST
import globals
from loggr import LOG
import helpers.config as config
from diffprivlib_json.diffprivl import DIFFPRIVLIBP_VERSION, dppipe_predict, dppipe_deserielize_train
from example_inputs import (example_diffprivlib, example_opendp,
                            example_opendp_str)
from helpers.depends import (competition_live, competition_prereq,
                             submit_limitter)
from helpers.leaderboard import LeaderBoard
from helpers.time import anti_timing_att
from input_models import DiffPrivLibInp, OpenDPInp, SNSQLInp, SNSynthInp
from mongodb.db_functions import (db_add_query, db_add_submission,
                                  db_add_teams, db_get_accuracy, db_get_budget,
                                  db_get_delta, db_get_last_submission,
                                  db_get_leaderboard, db_get_score)
from mongodb.db_models import QueryDBInput, SubmissionDBInput
from mongodb import client
# from oracle.stats import DPStats
from oracle.accuracy import accuracy as oracle_accuracy
from smartnoise_json.synth import synth

# from opendp_json import des_trans_ret
# from opendp.mod import enable_features
# enable_features('contrib')

"""class ModelType(BaseModel):
    model_type: str

    @validator('model_type')
    def check_model_type(cls, v):
        if v > 10 or v < 0:
            raise ValueError('Epsilon must be within 0-10.')
        return v"""





app = FastAPI()
# a simple hack to hinder the timing attackers in the audience
@app.middleware('http')
async def middleware(request: Request, call_next):
    # print(request.__dict__)
    return await anti_timing_att(request, call_next)

@app.get("/")
def hello():
    # db_add_teams()
    # db_get_last_query_time("Alice")
    print(db_get_last_submission("Bob"))
    print(db_get_last_submission("Alice"))
    return "Hello"

@app.on_event("startup")
def startup_event():
    LOG.info("Loading datasets")
    try:
        globals.set_datasets_fromDB()
    except Exception as e:
        LOG.error("Failed at startup:" + str(e))
        globals.SERVER_STATE["state"].append("Loading datasets at Startup Failure")
        globals.SERVER_STATE["message"].append(str(e))
    else:
        globals.SERVER_STATE["state"].append("Startup Completed")
        globals.SERVER_STATE["message"].append("Datasets Loaded!")


@app.get("/state", tags=["OBLV_ADMIN_USER"])
async def get_state(x_oblv_user_name: str = Header(None)):
    return {
        "requested_by": x_oblv_user_name,
        "state": globals.SERVER_STATE
    }
@app.post(
    "/train_data", 
    dependencies=[Depends(competition_prereq)],
    tags=["OBLV_ADMIN_USER"]
    )
def upload_train_data(
    file: UploadFile = File(...),
    x_oblv_user_name: str = Header(None)
    ):
    globals.set_TRAIN(file)

    globals.check_start_condition()

    return 'ok'

@app.post(
    "/test_data", 
    dependencies=[Depends(competition_prereq)],
    tags=["OBLV_ADMIN_USER"]
    )
def upload_test_data(
    file: UploadFile = File(...),
    x_oblv_user_name: str = Header(None)
    ):
    globals.set_TEST(file)

    globals.check_start_condition()

    return 'ok'

@app.get(
    "/start", 
    dependencies=[Depends(competition_prereq)],
    tags=["OBLV_ADMIN_USER"]
    )
def configure(
    # slack_path:str,
    x_oblv_user_name: str = Header(None)
    ):
    slack_path = "TV19HHM24/B044ZGKDNP6/5iikIvB7AP85eJZ7y4UgwQFs"
    config_ = config.get_settings()
    
    globals.LEADERBOARD = LeaderBoard(
        config_.parties,
        slack_path 
    )
    LOG.info("blabla")
    globals.check_start_condition()

    return "ok"


@app.post("/opendp", tags=["OBLV_PARTICIPANT_USER"])
def opendp_handler(pipeline_json: OpenDPInp = Body(example_opendp), x_oblv_user_name: str = Header(None)):
    
    return des_trans_ret(pipeline_json)
    
    pass# reconstruct the obj from the json string
    # print(pipeline_json.toJSONStr())
    # print(type(pipeline_json.toJSONStr()))
    # test = opendp_constructor(pipeline_json.toJSONStr(), ptype="json")
    
    # print(test.__dict__)
    # # res = opendp_constructor(example_opendp, ptype="json")
    # return str(test) # save the 


@app.post("/diffprivlib", tags=["OBLV_PARTICIPANT_USER"])
def diffprivlib_handler(pipeline_json: str = Body(example_diffprivlib), 
                            x_oblv_user_name: str = Header(...)):
    # if pipeline_json.version != DIFFPRIVLIBP_VERSION:
    #     raise HTTPException(422, f"For DiffPrivLib version {pipeline_json.version} is not supported, we currently have version:{DIFFPRIVLIBP_VERSION}")
    response, spent_budget, db_response = dppipe_deserielize_train(pipeline_json)
    # print(x_oblv_user_name)
    query = QueryDBInput(x_oblv_user_name,pipeline_json,"diffprivlib")
    query.query.epsilon = spent_budget["epsilon"]
    query.query.delta = spent_budget["delta"]
    query.query.response = str(db_response)
    db_add_query(query)

    return response
    
@app.post("/smartnoise_synth", tags=["OBLV_PARTICIPANT_USER"])
async def smartnoise_synth_handler(model_json: SNSynthInp, x_oblv_user_name: str = Header(None)):
    #Check for params
    # params = {}
    # create synthetic data using the specified model
    response = synth(model_json.model, model_json.epsilon)
    query = QueryDBInput(x_oblv_user_name,model_json.toJSON(),"smartnoise_synth")
    # query.query.epsilon = 10
    # query.query.delta = 10
    # query.query.response = {"key": "value"}
    db_add_query(query)
    # Not needed anymore
    # globals.LEADERBOARD.update_eps(x_oblv_user_name, model_json.epsilon)
    return response

@app.post("/smartnoise_sql_cost", tags=["OBLV_PARTICIPANT_USER"])
def smartnoise_sql_cost(query_json: SNSQLInp, x_oblv_user_name: str = Header(None)):
    response = globals.QUERIER.cost(query_json.query_str, query_json.epsilon, query_json.delta)
    
    return response

#estimate SQL query cost --- so that users can calculate before spending actually ----- 
@app.post("/smartnoise_sql", dependencies=[Depends(competition_live)], tags=["OBLV_PARTICIPANT_USER"])
def smartnoise_sql_handler(query_json: SNSQLInp, x_oblv_user_name: str = Header(None)):
    # Aggregate SQL-query on the ground truth data
    response = globals.QUERIER.query(query_json.query_str, query_json.epsilon, query_json.delta)
    query = QueryDBInput(x_oblv_user_name,query_json.toJSON(),"smartnoise")
    # query.query.epsilon = 10
    # query.query.delta = 10
    # query.query.response = {"key": "value"}
    db_add_query(query)
    # Not needed anymore
    # globals.LEADERBOARD.update_eps(x_oblv_user_name, query_json.epsilon)
    return response




@app.get(
    "/budget", 
    dependencies=[Depends(competition_live)],
    tags=["OBLV_PARTICIPANT_USER"]
    )
def budget(
    x_oblv_user_name: str = Header(None)
    ):
    return db_get_budget(x_oblv_user_name)

@app.get(
    "/accuracy", 
    dependencies=[Depends(competition_live)],
    tags=["OBLV_PARTICIPANT_USER"]
    )
def accuracy(
    x_oblv_user_name: str = Header(None)
    ):
    return db_get_accuracy(x_oblv_user_name)

@app.get(
    "/delta", 
    dependencies=[Depends(competition_live)],
    tags=["OBLV_PARTICIPANT_USER"]
    )
def accuracy(
    x_oblv_user_name: str = Header(None)
    ):
    return db_get_delta(x_oblv_user_name)

@app.get(
    "/score", 
    dependencies=[Depends(competition_live)],
    tags=["OBLV_PARTICIPANT_USER"]
    )
def score(
    x_oblv_user_name: str = Header(None)
    ):
    return db_get_score(x_oblv_user_name)

@app.post(
    "/submit", 
    dependencies=[
        # Depends(competition_live), 
        Depends(submit_limitter)
    ],
    tags=["OBLV_PARTICIPANT_USER"]
    )
def submit(
    # file: UploadFile = File(...),
    x_oblv_user_name: str = Header(None)
    ):
    # print(f"Recieved submission from {x_oblv_user_name}")
    # return oracle_accuracy(file, x_oblv_user_name)

    #TODO :CALCULATE SCORE
    # db_add_submission(x_oblv_user_name, SubmissionDBInput(18, 39))
    return #oracle_accuracy(file, x_oblv_user_name)


@app.get(
    "/leaderboard", 
    # dependencies=[Depends(competition_live)],
    tags=["OBLV_ADMIN_USER"]
    )
def get_leaderboard(
    x_oblv_user_name: str = Header(None)
    ):
    return db_get_leaderboard()

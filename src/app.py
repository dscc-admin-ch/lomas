import re
from urllib import response
from fastapi import Body, FastAPI, Depends, Request, Header, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from helpers.leaderboard import LeaderBoard
from helpers.time import anti_timing_att
from helpers.depends import competition_live, submit_limitter, competition_prereq
import helpers.config as config
# from oracle.stats import DPStats
# from oracle.accuracy import accuracy as oracle_accuracy
from smartnoise_json.synth import synth

# LEADERBOARD, QUERIER, TRAIN, TEST, LIVE, set_TRAIN, set_TEST
import globals  

from input_models import OpenDPInp, DiffPrivLibInp, SNSQLInp, SNSynthInp
from example_inputs import example_diffprivlib, example_opendp, example_opendp_str
from diffprivlib_json.diffprivl import DIFFPRIVLIBP_VERSION, dppipe_predict
# from opendp_json import opendp_constructor
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
    print(request.__dict__)
    return await anti_timing_att(request, call_next)


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
    db_user:str,
    db_pass:str,
    x_oblv_user_name: str = Header(None)
    ):
    slack_path = "TV19HHM24/B044ZGKDNP6/5iikIvB7AP85eJZ7y4UgwQFs"
    config_ = config.get_settings()
    
    globals.LEADERBOARD = LeaderBoard(
        config_.parties,
        slack_path 
    )

    globals.check_start_condition()

    return "ok"


@app.post("/opendp", tags=["OBLV_PARTICIPANT_USER"])
def opendp_handler(pipeline_json: OpenDPInp = Body(example_opendp), x_oblv_user_name: str = Header(None)):
    pass# reconstruct the obj from the json string
    # print(pipeline_json.toJSONStr())
    # print(type(pipeline_json.toJSONStr()))
    # test = opendp_constructor(pipeline_json.toJSONStr(), ptype="json")
    
    # print(test.__dict__)
    # # res = opendp_constructor(example_opendp, ptype="json")
    # return str(test) # save the 


@app.post("/diffprivlib", tags=["OBLV_PARTICIPANT_USER"])
def diffprivlib_handler(pipeline_json: DiffPrivLibInp = Body(example_diffprivlib), 
                            x_oblv_user_name: str = Header(None)):
    if pipeline_json.version != DIFFPRIVLIBP_VERSION:
        raise HTTPException(422, f"For DiffPrivLib version {pipeline_json.version} is not supported, we currently have version:{DIFFPRIVLIBP_VERSION}")
    model_file = dppipe_predict(pipeline_json=pipeline_json.toJSON()["pipeline"])
    return FileResponse(model_file, media_type='application/octet-stream',filename="diffprivlib_trained_pipeline.pkl") #return accuracy, --, actual model


@app.post("/smartnoise_synth", tags=["OBLV_PARTICIPANT_USER"])
async def smartnoise_synth_handler(model_json: SNSynthInp, x_oblv_user_name: str = Header(None)):
    #Check for params
    # params = {}
    # create synthetic data using the specified model
    response = synth(model_json.model, model_json.epsilon)
    globals.LEADERBOARD.update_eps(x_oblv_user_name, model_json.epsilon)
    return response

@app.post("/snsql_cost")
def smartnoise_sql_cost(query_json: SNSQLInp, x_oblv_user_name: str = Header(None)):
    response = globals.QUERIER.cost(query_json.query_str, query_json.epsilon, query_json.delta)
    
    return response

#estimate SQL query cost --- so that users can calculate before spending actually ----- 
@app.post("/smartnoise_sql", dependencies=[Depends(competition_live)], tags=["OBLV_PARTICIPANT_USER"])
def smartnoise_sql_handler(query_json: SNSQLInp, x_oblv_user_name: str = Header(None)):
    # Aggregate SQL-query on the ground truth data
    response = globals.QUERIER.query(query_json.query_str, query_json.epsilon, query_json.delta)
    globals.LEADERBOARD.update_eps(x_oblv_user_name, query_json.epsilon)
    return response




# @app.get(
#     "/budget", 
#     dependencies=[Depends(competition_live)],
#     tags=["OBLV_PARTICIPANT_USER"]
#     )
# def budget(
#     x_oblv_user_name: str = Header(None)
#     ):
#     return globals.LEADERBOARD.get_eps(x_oblv_user_name)

# @app.get(
#     "/accuracy", 
#     dependencies=[Depends(competition_live)],
#     tags=["OBLV_PARTICIPANT_USER"]
#     )
# def accuracy(
#     x_oblv_user_name: str = Header(None)
#     ):
#     return globals.LEADERBOARD.get_acc(x_oblv_user_name)

# @app.get(
#     "/score", 
#     dependencies=[Depends(competition_live)],
#     tags=["OBLV_PARTICIPANT_USER"]
#     )
# def score(
#     x_oblv_user_name: str = Header(None)
#     ):
#     return globals.LEADERBOARD.get_score(x_oblv_user_name)

# @app.post(
#     "/submit", 
#     dependencies=[
#         Depends(competition_live), 
#         Depends(submit_limitter)
#     ],
#     tags=["OBLV_PARTICIPANT_USER"]
#     )
# def submit(
#     file: UploadFile = File(...),
#     x_oblv_user_name: str = Header(None)
#     ):
#     print(f"Recieved submission from {x_oblv_user_name}")
#     return oracle_accuracy(file, x_oblv_user_name)


@app.get(
    "/leaderboard", 
    dependencies=[Depends(competition_live)],
    tags=["OBLV_ADMIN_USER"]
    )
def get_leaderboard(
    x_oblv_user_name: str = Header(None)
    ):
    return globals.LEADERBOARD.to_fast_api_csv_str()

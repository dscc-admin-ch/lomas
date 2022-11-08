from fastapi import (Body, Depends, FastAPI, File, Header, HTTPException,
                     Request, UploadFile)
import globals
from loggr import LOG
from diffprivlib_json.diffprivl import dppipe_deserielize_train
from example_inputs import (example_diffprivlib, example_opendp,
                            example_smartnoise_sql, example_smartnoise_synth)
from helpers.depends import (competition_live,
                             submit_limitter)
from helpers.time import anti_timing_att
from input_models import DiffPrivLibInp, OpenDPInp, SNSQLInp, SNSynthInp
from mongodb.db_functions import (db_add_query, db_add_submission,
                                  db_add_teams, db_get_accuracy, db_get_budget,
                                  db_get_delta, db_get_leaderboard, db_get_score)
from mongodb.db_models import QueryDBInput, SubmissionDBInput
from opendp_json.opdp import opendp_constructor, opendp_apply
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


@app.on_event("startup")
def startup_event():
    LOG.info("Loading teams")
    try:
        db_add_teams()
    except Exception as e:
        LOG.exception("Failed while loading teams at startup:" + str(e))
        globals.SERVER_STATE["state"].append("Loading teams at Startup Failure")
        globals.SERVER_STATE["message"].append(str(e))
    else:
        globals.SERVER_STATE["state"].append("Teams Loaded")
        globals.SERVER_STATE["message"].append("Success!")
    
    LOG.info("Loading datasets")
    try:
        globals.set_datasets_fromDB()
    except Exception as e:
        LOG.exception("Failed at startup:" + str(e))
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


@app.post("/opendp", dependencies=[Depends(competition_live)], tags=["OBLV_PARTICIPANT_USER"])
def opendp_handler(pipeline_json: OpenDPInp = Body(example_opendp), x_oblv_user_name: str = Header(None)):
    
    try:
        opendp_pipe = opendp_constructor(pipeline_json.toJSONStr())
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(500, "Failed while contructing opendp pipeline with error: " + str(e))
    try:
        response, privacy_map = opendp_apply(opendp_pipe)
    except HTTPException as he:
        LOG.exception(he)
        raise he
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(500, str(e))
        
    query = QueryDBInput(x_oblv_user_name,pipeline_json,"opendp")
    query.query.epsilon = privacy_map[0]
    query.query.delta = privacy_map[1]
    query.query.response = str(response)
    db_add_query(query)


    return response


@app.post("/diffprivlib", dependencies=[Depends(competition_live)], tags=["OBLV_PARTICIPANT_USER"])
def diffprivlib_handler(pipeline_json: DiffPrivLibInp = Body(example_diffprivlib), 
                            x_oblv_user_name: str = Header(...)):
    # if pipeline_json.version != DIFFPRIVLIBP_VERSION:
    #     raise HTTPException(422, f"For DiffPrivLib version {pipeline_json.version} is not supported, we currently have version:{DIFFPRIVLIBP_VERSION}")
    try:
        response, spent_budget, db_response = dppipe_deserielize_train(pipeline_json.toJSONStr(), pipeline_json.y_column)
    except HTTPException as he:
        LOG.exception(he)
        raise he
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(500, f"Error message: {e}")
    # print(x_oblv_user_name)
    query = QueryDBInput(x_oblv_user_name,pipeline_json,"diffprivlib")
    query.query.epsilon = spent_budget["epsilon"]
    query.query.delta = spent_budget["delta"]
    query.query.response = db_response
    db_add_query(query)

    return response
    
@app.post("/smartnoise_synth", dependencies=[Depends(competition_live)], tags=["OBLV_PARTICIPANT_USER"])
def smartnoise_synth_handler(model_inp: SNSynthInp = Body(example_smartnoise_synth), x_oblv_user_name: str = Header(None)):
    try:
        response = synth(model_inp)
    except HTTPException as he:
        LOG.exception(he)
        raise he
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(500, f"Please check epsilon and delta are provided. Error message: {str(e)}")
    query = QueryDBInput(x_oblv_user_name,model_inp.toJSON(),"smartnoise_synth")
    query.query.epsilon = model_inp.epsilon
    query.query.delta = model_inp.delta
    query.query.response = str(response)
    db_add_query(query)
    return response

@app.post("/smartnoise_sql_cost", dependencies=[Depends(competition_live)], tags=["OBLV_PARTICIPANT_USER"])
def smartnoise_sql_cost(query_json: SNSQLInp = Body(example_smartnoise_sql), x_oblv_user_name: str = Header(None)):
    try:
        response = globals.QUERIER.cost(query_json.query_str, query_json.epsilon, query_json.delta)
    except HTTPException as he:
        LOG.exception(he)
        raise he
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(500, str(e))
    
    return response

#estimate SQL query cost --- so that users can calculate before spending actually ----- 
@app.post("/smartnoise_sql", dependencies=[Depends(competition_live)], tags=["OBLV_PARTICIPANT_USER"])
def smartnoise_sql_handler(query_json: SNSQLInp = Body(example_smartnoise_sql), x_oblv_user_name: str = Header(None)):
    # Aggregate SQL-query on the ground truth data
    try:
        response, privacy_cost, db_res = globals.QUERIER.query(query_json.query_str, query_json.epsilon, query_json.delta)
    except HTTPException as he:
        LOG.exception(he)
        raise he
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(500, str(e))
    query = QueryDBInput(x_oblv_user_name,query_json.toJSON(),"smartnoise_sql")
    query.query.epsilon = privacy_cost[0]
    query.query.delta = privacy_cost[1]
    query.query.response = db_res
    db_add_query(query)
    return response




@app.get(
    "/total_epsilon", 
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
    "/total_delta", 
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
        Depends(competition_live), 
        Depends(submit_limitter)
    ],
    tags=["OBLV_PARTICIPANT_USER"]
    )
def submit(
    file: UploadFile = File(...),
    x_oblv_user_name: str = Header(None)
    ):
    LOG.info(f"Recieved submission from {x_oblv_user_name}")
    #TODO :CALCULATE SCORE

    acc, score, f_acc, f_score, sdata = oracle_accuracy(file, x_oblv_user_name)
    db_entry = SubmissionDBInput(acc, score, final_accuracy=f_acc, final_score=f_score, data=sdata.to_dict())
    db_add_submission(x_oblv_user_name, db_entry)

    return f"Submission accepted. This submission had an accuracy of {acc}. Your total score is: {score}"
    


@app.get(
    "/leaderboard", 
    # dependencies=[Depends(competition_live)],
    tags=["OBLV_ADMIN_USER"]
    )
def get_leaderboard(
    x_oblv_user_name: str = Header(None)
    ):
    return db_get_leaderboard()

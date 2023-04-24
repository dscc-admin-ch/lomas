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
from opendp_json.opdp import opendp_constructor, opendp_apply
# from oracle.stats import DPStats
from oracle.accuracy import accuracy as oracle_accuracy
from smartnoise_json.synth import synth

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
        #db_add_teams()
        print("ignoring startup event..")
    except Exception as e:
        LOG.exception("Failed while loading teams at startup:" + str(e))
        globals.SERVER_STATE["state"].append("Loading teams at Startup Failure")
        globals.SERVER_STATE["message"].append(str(e))
    else:
        globals.SERVER_STATE["state"].append("Teams Loaded")
        globals.SERVER_STATE["message"].append("Success!")
    
    LOG.info("Loading datasets")
    try:
        #globals.set_datasets_fromDB()
    except Exception as e:
        LOG.exception("Failed at startup:" + str(e))
        globals.SERVER_STATE["state"].append("Loading datasets at Startup Failure")
        globals.SERVER_STATE["message"].append(str(e))
    else:
        globals.SERVER_STATE["state"].append("Startup Completed")
        globals.SERVER_STATE["message"].append("Datasets Loaded!")
    globals.check_start_condition()


@app.get("/state", tags=["OBLV_ADMIN_USER"])
async def get_state(x_oblv_user_name: str = Header(None)):
    return {
        "requested_by": x_oblv_user_name,
        "state": globals.SERVER_STATE
    }
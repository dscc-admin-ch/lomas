from fastapi import Depends, FastAPI, Header, Request

import globals
from database.yaml_database import YamlDatabase
from dp_queries.input_models import SNSQLInp
from utils.anti_timing_att import anti_timing_att
from utils.depends import server_live
from utils.config import get_config
from utils.loggr import LOG


# This object holds the server object
app = FastAPI()


@app.on_event("startup")
def startup_event():
    """
    This function is executed once on server startup"""
    LOG.info("Startup message")

    # Load config here
    _ = get_config()

    # Load users, datasets, etc..
    LOG.info("Loading user database")
    globals.USER_DATABASE = YamlDatabase()

    LOG.info("Loading datasets")
    try:
        globals.set_datasets_fromDB()
    except Exception as e:
        LOG.exception("Failed at startup:" + str(e))
        globals.SERVER_STATE["state"].append(
            "Loading datasets at Startup Failure"
        )
        globals.SERVER_STATE["message"].append(str(e))
    else:
        globals.SERVER_STATE["state"].append("Startup Completed")
        globals.SERVER_STATE["message"].append("Datasets Loaded!")

    # Finally check everything in startup went well and update the state
    globals.check_start_condition()


# A simple hack to hinder the timing attackers
@app.middleware("http")
async def middleware(request: Request, call_next):
    return await anti_timing_att(request, call_next)


# Example implementation for an endpoint
@app.get("/state", tags=["OBLV_ADMIN_USER"])
async def get_state(x_oblv_user_name: str = Header(None)):
    """
    Some __custom__ documentation about this endoint.

    Returns the current state dict of this server instance.
    """
    """
    Code Documentation in a second comment.
    """
    return {
        "requested_by": x_oblv_user_name,
        "state": globals.SERVER_STATE,
    }


# estimate SQL query cost --- so that users can calculate before spending actually -----
@app.post("/smartnoise_sql", tags=["OBLV_PARTICIPANT_USER"])
def smartnoise_sql_handler(
    query_json: SNSQLInp = Body(example_smartnoise_sql),
    x_oblv_user_name: str = Header(None),
):
    response = dp_query_logic("smartnoise_sql", query_json, x_oblv_user_name)

    # Return response
    return response


@app.get("/submit_limit", dependencies=[Depends(server_live)])
async def get_submit_limit():
    """
    Returns the value "submit_limit" used to limit the rate of submissions
    """
    """
    An endpoint example with some dependecies.

    Dummy endpoint to exemplify the use of the dependencies argument.
    The depends.server_live functoin is called and it must yield in order for
    this endpoint handler to execute.
    """

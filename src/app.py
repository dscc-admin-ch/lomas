from fastapi import (Body, Depends, FastAPI, File, Header, HTTPException,
                     Request, UploadFile)
import globals
from helpers.loggr import LOG
from helpers.depends import (server_live)
from helpers.anti_timing_att import anti_timing_att
from helpers.config import get_config

# This object holds the server object
app = FastAPI()


@app.on_event("startup")
def startup_event():
    """
    This function is executed once on server startup"""
    LOG.info("Startup message")
    
    # Load config here
    config = get_config()
    # Load users, datasets, etc..

    # Do more startup initialization stuff (possibly try-catch blocks)

    # Finally check everything in startup went well and update the state
    globals.check_start_condition()


# A simple hack to hinder the timing attackers
@app.middleware('http')
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
        "state": globals.SERVER_STATE
    }

@app.get("/submit_limit", dependencies=[Depends(server_live)])
async def get_submit_limit():
    """Returns the value "submit_limit" used to limit the rate of submissions
    """
    """
    An endpoint example with some dependecies.

    Dummy endpoint to exemplify the use of the dependencies argument.
    The depends.server_live functoin is called and it must yield in order for
    this endpoint handler to execute.
    """

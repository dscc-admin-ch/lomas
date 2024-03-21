from fastapi import FastAPI, Request
from pydantic import BaseModel

from utils.loggr import LOG


class JSONToLog(BaseModel):
    message: str


# This object holds the server object
app = FastAPI()


# Startup
# -----------------------------------------------------------------------------


@app.on_event("startup")
def startup_event():
    """
    This function is executed once on server startup
    """


# API Endpoints
# -----------------------------------------------------------------------------


@app.get("/")
async def home():
    """
    Returns the current state dict of this server instance.
    """
    return {"message": "Hello World"}


@app.get("/get_headers")
async def get_headers(request: Request):

    return {"headers": request.headers}


@app.post("/log_body")
async def log_body(json_to_log: JSONToLog):

    LOG.info(json_to_log.message)

    return {"message": "Success"}

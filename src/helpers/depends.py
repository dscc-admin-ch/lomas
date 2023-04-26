from fastapi import FastAPI, Depends, Request, Header, HTTPException
import globals
from time import time

async def server_live():
    if not globals.SERVER_STATE["LIVE"]:
        raise HTTPException(
            status_code=403, 
            detail= "Woops, the server did not start correctly. Contact the administrator of this service."
        )
    yield

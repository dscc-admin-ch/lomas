from fastapi import FastAPI, Depends, Request, Header, HTTPException
import globals
import helpers.config as config
from time import time
from mongodb.db_functions import db_get_last_submission

async def competition_live():
    if not globals.LIVE:
        raise HTTPException(
            status_code=403, 
            detail= "Woops, this competition has not yet started! Please wait until the organizers notify you otherwise."
        )
    yield

async def competition_prereq():
    if globals.LIVE:
        raise HTTPException(
            status_code=403, 
            detail= "Application already configured and the competition has started."
        )
    yield

async def submit_limitter(x_oblv_user_name: str = Header(None)):
    config_ = config.get_settings()
    # assert globals.LEADERBOARD._status[x_oblv_user_name], f"{x_oblv_user_name} is not a valid name"
    # last_call = globals.LEADERBOARD._status[x_oblv_user_name].last_submision
    
    last_call = db_get_last_submission(x_oblv_user_name)
    if last_call:
        if (time() - last_call) < config_.submit_limit:
            raise HTTPException(
                status_code=403, 
                detail= f"Uh Oh! You can only submit a new result {config_.submit_limit} secs after the last submision. {int(config_.submit_limit - (time() - last_call))} seconds remaining until you can submit again."
            )
    yield

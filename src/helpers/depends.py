from fastapi import FastAPI, Depends, Request, Header, HTTPException
import globals
import helpers.config as config
from datetime import datetime

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
    assert globals.LEADERBOARD._status[x_oblv_user_name], f"{x_oblv_user_name} is not a valid name"
    last_call = globals.LEADERBOARD._status[x_oblv_user_name].last_submision
    if last_call:
        if (datetime.now() - last_call).total_seconds() < config_.submit_limit:
            raise HTTPException(
                status_code=403, 
                detail= f"Uh Oh! You can only submit a new result {config_.submit_limit} secs after the last submision. {config_.submit_limit - (datetime.now() - last_call).total_seconds()} seconds remaining until you can submit again."
            )
    yield

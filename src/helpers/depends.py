from fastapi import HTTPException
import globals


async def server_live():
    if not globals.SERVER_STATE["LIVE"]:
        raise HTTPException(
            status_code=403,
            detail="Woops, the server did not start correctly. \
                Contact the administrator of this service.",
        )
    yield

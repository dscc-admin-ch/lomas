import io
from typing import AsyncGenerator

import app
import pandas as pd
from constants import (
    CONFIG_NOT_LOADED,
    DB_NOT_LOADED,
    QUERY_HANDLER_NOT_LOADED,
    SERVER_LIVE,
)
from fastapi.responses import StreamingResponse
from utils.error_handler import InternalServerException
from utils.loggr import LOG


def stream_dataframe(df: pd.DataFrame) -> StreamingResponse:
    stream = io.StringIO()

    # CSV creation
    df.to_csv(stream, index=False)

    response = StreamingResponse(
        iter([stream.getvalue()]), media_type="text/csv"
    )
    response.headers[
        "Content-Disposition"
    ] = "attachment; filename=synthetic_data.csv"
    return response


async def server_live() -> AsyncGenerator:
    if not app.SERVER_STATE["LIVE"]:
        raise InternalServerException(
            "Woops, the server did not start correctly."
            + "Contact the administrator of this service.",
        )
    yield


def check_start_condition() -> None:
    """
    This function checks the server started correctly and SERVER_STATE is
    updated accordingly.

    This has potential side effects on the return values of the "depends"
    functions, which check the server state.
    """
    status_ok = True
    if app.CONFIG is None:
        LOG.info("Config not loaded")
        app.SERVER_STATE["state"].append(CONFIG_NOT_LOADED)
        app.SERVER_STATE["message"].append("Server could not be started!")
        app.SERVER_STATE["LIVE"] = False
        status_ok = False

    if app.ADMIN_DATABASE is None:
        LOG.info("Admin database not loaded")
        app.SERVER_STATE["state"].append(DB_NOT_LOADED)
        app.SERVER_STATE["message"].append("Server could not be started!")
        app.SERVER_STATE["LIVE"] = False
        status_ok = False

    if app.QUERY_HANDLER is None:
        LOG.info("QueryHandler not loaded")
        app.SERVER_STATE["state"].append(QUERY_HANDLER_NOT_LOADED)
        app.SERVER_STATE["message"].append("Server could not be started!")
        app.SERVER_STATE["LIVE"] = False
        status_ok = False

    if status_ok:
        LOG.info("Server start condition OK")
        app.SERVER_STATE["state"].append(SERVER_LIVE)
        app.SERVER_STATE["message"].append("Server start condition OK")
        app.SERVER_STATE["LIVE"] = True

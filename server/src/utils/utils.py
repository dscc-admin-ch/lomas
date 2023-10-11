import io
from fastapi.responses import StreamingResponse
from functools import partial

import app
from admin_database.admin_database import AdminDatabase
from constants import (
    CONFIG_NOT_LOADED,
    DB_NOT_LOADED,
    QUERY_HANDLER_NOT_LOADED,
    SERVER_LIVE,
)
from utils.config import Config
from utils.loggr import LOG
from dp_queries.dp_logic import QueryHandler


def stream_dataframe(df):
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


def check_start_condition(
    server_state: dict,
    config: Config,
    admin_database: AdminDatabase,
    query_handler: QueryHandler,
):
    """
    This function checks the server started correctly and server_state is
    updated accordingly.

    This has potential side effects on the return values of the "depends"
    functions, which check the server state.
    """
    status_ok = True
    if config is None:
        LOG.info("config not loaded")
        server_state["state"].append(CONFIG_NOT_LOADED)
        server_state["message"].append("Server could not be started!")
        server_state["LIVE"] = False
        status_ok = False

    if admin_database is None:
        LOG.info("Admin database not loaded")
        server_state["state"].append(DB_NOT_LOADED)
        server_state["message"].append("Server could not be started!")
        server_state["LIVE"] = False
        status_ok = False

    if query_handler is None:
        LOG.info("QueryHandler not loaded")
        server_state["state"].append(QUERY_HANDLER_NOT_LOADED)
        server_state["message"].append("Server could not be started!")
        server_state["LIVE"] = False
        status_ok = False

    if status_ok:
        LOG.info("Server start condition OK")
        server_state["state"].append(SERVER_LIVE)
        server_state["message"].append("Server start condition OK")
        server_state["LIVE"] = True


async def server_live():
    if not app.SERVER_STATE["LIVE"]:
        raise HTTPException(
            status_code=403,
            detail="Woops, the server did not start correctly. \
                Contact the administrator of this service.",
        )
    yield
    
from typing import Callable, Dict, List, Union

from admin_database.admin_database import AdminDatabase
from admin_database.utils import database_factory
from constants import DPLibraries
from dataset_store.utils import dataset_store_factory
from dp_queries.dp_libraries.utils import querier_factory
from dp_queries.dp_logic import QueryHandler
from dp_queries.dummy_dataset import (
    get_dummy_dataset_for_query,
    make_dummy_dataset,
)
from fastapi import Body, Depends, FastAPI, Header, Request, Response
from fastapi.responses import StreamingResponse
from mongodb_admin import (
    add_datasets,
    create_users_collection,
    drop_collection,
)
from utils.anti_timing_att import anti_timing_att
from utils.config import Config, get_config
from utils.error_handler import (
    InternalServerException,
    add_exception_handlers,
    get_custom_exceptions_list,
)
from utils.example_inputs import (
    example_dummy_opendp,
    example_dummy_smartnoise_sql,
    example_get_db_data,
    example_get_dummy_dataset,
    example_opendp,
    example_smartnoise_sql,
    example_smartnoise_sql_cost,
)
from utils.input_models import (
    DummyOpenDPInp,
    DummySNSQLInp,
    GetDbData,
    GetDummyDataset,
    OpenDPInp,
    SNSQLInp,
    SNSQLInpCost,
)
from utils.loggr import LOG
from utils.utils import check_start_condition, server_live, stream_dataframe

# Some global variables
# -----------------------------------------------------------------------------
CONFIG: Config = None
ADMIN_DATABASE: AdminDatabase = None
QUERY_HANDLER: QueryHandler = None

# General server state, can add fields if need be.
SERVER_STATE: dict = {
    "state": [],
    "message": [],
    "LIVE": False,
}

# This object holds the server object
app = FastAPI()


# Startup
# -----------------------------------------------------------------------------


@app.on_event("startup")
def startup_event() -> None:
    """
    This function is executed once on server startup"""
    LOG.info("Startup message")
    SERVER_STATE["state"].append("Startup event")

    # Load config here
    LOG.info("Loading config")
    SERVER_STATE["message"].append("Loading config")
    global CONFIG
    CONFIG = get_config()

    # Fill up user database if in develop mode ONLY
    if CONFIG.develop_mode:
        LOG.info("!! Develop mode ON !!")
        LOG.info("Creating example user collection")
        from types import SimpleNamespace

        args = SimpleNamespace(**vars(CONFIG.admin_database))

        LOG.info("Creating user collection")
        args.clean = True
        args.overwrite = True
        args.path = "/data/collections/user_collection.yaml"
        create_users_collection(args)

        LOG.info("Creating datasets and metadata collection")
        args.path = "/data/collections/dataset_collection.yaml"
        args.overwrite_datasets = True
        args.overwrite_metadata = True
        add_datasets(args)

        LOG.info("Empty archives")
        args.collection = "queries_archives"
        drop_collection(args)

    # Load users, datasets, etc..
    LOG.info("Loading admin database")
    SERVER_STATE["message"].append("Loading admin database")
    try:
        global ADMIN_DATABASE
        ADMIN_DATABASE = database_factory(CONFIG.admin_database)
    except Exception as e:
        LOG.exception("Failed at startup:" + str(e))
        SERVER_STATE["state"].append("Loading user database at Startup failed")
        SERVER_STATE["message"].append(str(e))

    LOG.info("Loading query handler")
    SERVER_STATE["message"].append("Loading dataset store")
    dataset_store = dataset_store_factory(CONFIG.dataset_store, ADMIN_DATABASE)

    SERVER_STATE["message"].append("Loading query handler")
    global QUERY_HANDLER
    QUERY_HANDLER = QueryHandler(ADMIN_DATABASE, dataset_store)

    SERVER_STATE["state"].append("Startup completed")
    SERVER_STATE["message"].append("Startup completed")

    # Finally check everything in startup went well and update the state
    check_start_condition()


# A simple hack to hinder the timing attackers
@app.middleware("http")
async def middleware(request: Request, call_next: Callable) -> Response:
    global CONFIG
    return await anti_timing_att(request, call_next, CONFIG)


# Add custom exception handlers
add_exception_handlers(app)
custom_exceptions = get_custom_exceptions_list()

# API Endpoints
# -----------------------------------------------------------------------------


# Get server state
@app.get("/state", tags=["ADMIN_USER"])
async def get_state(
    user_name: str = Header(None),
) -> Dict[str, Union[str, Dict[str, Union[List[str], bool]]]]:
    """
    Returns the current state dict of this server instance.
    """
    return {
        "requested_by": user_name,
        "state": SERVER_STATE,
    }


# Metadata query
@app.post(
    "/get_dataset_metadata",
    dependencies=[Depends(server_live)],
    tags=["USER_METADATA"],
)
def get_dataset_metadata(
    query_json: GetDbData = Body(example_get_db_data),
) -> Dict[str, Union[int, bool, Dict[str, Union[str, int]]]]:
    try:
        ds_metadata = ADMIN_DATABASE.get_dataset_metadata(
            query_json.dataset_name
        )[""]["Schema"]["Table"]

    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return ds_metadata


# Dummy dataset query
@app.post(
    "/get_dummy_dataset",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def get_dummy_dataset(
    query_json: GetDummyDataset = Body(example_get_dummy_dataset),
) -> StreamingResponse:
    try:
        ds_metadata = ADMIN_DATABASE.get_dataset_metadata(
            query_json.dataset_name
        )

        dummy_df = make_dummy_dataset(
            ds_metadata, query_json.dummy_nb_rows, query_json.dummy_seed
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return stream_dataframe(dummy_df)


# Smartnoise SQL query
@app.post(
    "/smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def smartnoise_sql_handler(
    query_json: SNSQLInp = Body(example_smartnoise_sql),
    user_name: str = Header(None),
) -> dict:
    try:
        response = QUERY_HANDLER.handle_query(
            DPLibraries.SMARTNOISE_SQL, query_json, user_name
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return response


# Smartnoise SQL Dummy query
@app.post(
    "/dummy_smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_smartnoise_sql_handler(
    query_json: DummySNSQLInp = Body(example_dummy_smartnoise_sql),
) -> dict:
    ds_private_dataset = get_dummy_dataset_for_query(
        ADMIN_DATABASE, query_json
    )
    dummy_querier = querier_factory(
        DPLibraries.SMARTNOISE_SQL, private_dataset=ds_private_dataset
    )
    try:
        _ = dummy_querier.cost(query_json)  # verify cost works
        response_df = dummy_querier.query(query_json)
        response = {"query_response": response_df}
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return response


@app.post(
    "/estimate_smartnoise_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_smartnoise_cost(
    query_json: SNSQLInpCost = Body(example_smartnoise_sql_cost),
) -> Dict[str, float]:
    try:
        response = QUERY_HANDLER.estimate_cost(
            DPLibraries.SMARTNOISE_SQL,
            query_json,
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return response


@app.post(
    "/opendp_query", dependencies=[Depends(server_live)], tags=["USER_QUERY"]
)
def opendp_query_handler(
    query_json: OpenDPInp = Body(example_opendp),
    user_name: str = Header(None),
) -> dict:
    try:
        response = QUERY_HANDLER.handle_query(
            DPLibraries.OPENDP, query_json, user_name
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return response


@app.post(
    "/dummy_opendp_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_opendp_query_handler(
    query_json: DummyOpenDPInp = Body(example_dummy_opendp),
) -> dict:
    ds_private_dataset = get_dummy_dataset_for_query(
        ADMIN_DATABASE, query_json
    )
    dummy_querier = querier_factory(
        DPLibraries.OPENDP, private_dataset=ds_private_dataset
    )

    try:
        _ = dummy_querier.cost(query_json)  # verify cost works
        response_df = dummy_querier.query(query_json)
        response = {"query_response": response_df}

    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return response


@app.post(
    "/estimate_opendp_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_opendp_cost(
    query_json: OpenDPInp = Body(example_opendp),
) -> Dict[str, float]:
    try:
        response = QUERY_HANDLER.estimate_cost(
            DPLibraries.OPENDP,
            query_json,
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return response


# MongoDB get initial budget
@app.post(
    "/get_initial_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_initial_budget(
    query_json: GetDbData = Body(example_get_db_data),
    user_name: str = Header(None),
) -> Dict[str, float]:
    try:
        initial_epsilon, initial_delta = ADMIN_DATABASE.get_initial_budget(
            user_name, query_json.dataset_name
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return {"initial_epsilon": initial_epsilon, "initial_delta": initial_delta}


# MongoDB get total spent budget
@app.post(
    "/get_total_spent_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_total_spent_budget(
    query_json: GetDbData = Body(example_get_db_data),
    user_name: str = Header(None),
) -> Dict[str, float]:
    try:
        (
            total_spent_epsilon,
            total_spent_delta,
        ) = ADMIN_DATABASE.get_total_spent_budget(
            user_name, query_json.dataset_name
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return {
        "total_spent_epsilon": total_spent_epsilon,
        "total_spent_delta": total_spent_delta,
    }


# MongoDB get remaining budget
@app.post(
    "/get_remaining_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_remaining_budget(
    query_json: GetDbData = Body(example_get_db_data),
    user_name: str = Header(None),
) -> Dict[str, float]:
    try:
        rem_epsilon, rem_delta = ADMIN_DATABASE.get_remaining_budget(
            user_name, query_json.dataset_name
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return {"remaining_epsilon": rem_epsilon, "remaining_delta": rem_delta}


# MongoDB get archives
@app.post(
    "/get_previous_queries",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_user_previous_queries(
    query_json: GetDbData = Body(example_get_db_data),
    user_name: str = Header(None),
) -> Dict[str, float]:
    try:
        previous_queries = ADMIN_DATABASE.get_user_previous_queries(
            user_name, query_json.dataset_name
        )
    except custom_exceptions as e:
        raise e
    except Exception as e:
        raise InternalServerException(e)

    return {"previous_queries": previous_queries}

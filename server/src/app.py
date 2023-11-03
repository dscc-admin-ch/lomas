from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request

from mongodb_admin import MongoDB_Admin
from admin_database.admin_database import AdminDatabase
from admin_database.utils import database_factory, get_mongodb_url
from dataset_store.utils import dataset_store_factory
from dp_queries.dp_logic import QueryHandler
from utils.example_inputs import (
    example_dummy_opendp,
    example_dummy_smartnoise_sql,
    example_get_dataset_metadata,
    example_get_db_data,
    example_get_dummy_dataset,
    example_opendp,
    example_smartnoise_sql,
    example_smartnoise_sql_cost,
)
from utils.input_models import (
    DummyOpenDPInp,
    DummySNSQLInp,
    GetDatasetMetadata,
    GetDbData,
    GetDummyDataset,
    OpenDPInp,
    SNSQLInp,
    SNSQLInpCost,
)
from dp_queries.dp_libraries.open_dp import OpenDPQuerier
from dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier
from utils.utils import stream_dataframe, server_live, check_start_condition
from private_dataset.in_memory_dataset import InMemoryDataset
from utils.anti_timing_att import anti_timing_att
from utils.config import get_config, Config
from constants import (
    INTERNAL_SERVER_ERROR,
    LIB_OPENDP,
    LIB_SMARTNOISE_SQL,
)
from dp_queries.dummy_dataset import make_dummy_dataset
from utils.loggr import LOG

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
def startup_event():
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

        db_url = get_mongodb_url(CONFIG.admin_database)
        db_name = CONFIG.admin_database.db_name
        mongo_admin = MongoDB_Admin(db_url, db_name)

        def args():
            return None  # trick to create a dummy args object

        LOG.info("Creating user collection")
        args.path = "/data/collections/user_collection.yaml"
        mongo_admin.create_users_collection(args)

        LOG.info("Creating datasets and metadata collection")
        args.path = "/data/collections/dataset_collection.yaml"
        mongo_admin.add_datasets(args)

        del mongo_admin

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
async def middleware(request: Request, call_next):
    global CONFIG
    return await anti_timing_att(request, call_next, CONFIG)


# API Endpoints
# -----------------------------------------------------------------------------


@app.get("/state", tags=["ADMIN_USER"])
async def get_state(user_name: str = Header(None)):
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
    query_json: GetDatasetMetadata = Body(example_get_dataset_metadata),
):
    # Create dummy dataset based on seed and number of rows
    try:
        ds_metadata = ADMIN_DATABASE.get_dataset_metadata(
            query_json.dataset_name
        )

    except HTTPException as e:
        raise e

    return ds_metadata


# Dummy dataset query
@app.post(
    "/get_dummy_dataset",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def get_dummy_dataset(
    query_json: GetDummyDataset = Body(example_get_dummy_dataset),
):
    # Create dummy dataset based on seed and number of rows
    try:
        ds_metadata = ADMIN_DATABASE.get_dataset_metadata(
            query_json.dataset_name
        )

        dummy_df = make_dummy_dataset(
            ds_metadata, query_json.dummy_nb_rows, query_json.dummy_seed
        )
    except HTTPException as e:
        raise e

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
):
    # Catch all non-http exceptions so that the server does not fail.
    try:
        response = QUERY_HANDLER.handle_query(
            LIB_SMARTNOISE_SQL, query_json, user_name
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        LOG.info(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)

    # Return response
    return response


# Smartnoise SQL Dummy query
@app.post(
    "/dummy_smartnoise_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_smartnoise_sql_handler(
    query_json: DummySNSQLInp = Body(example_dummy_smartnoise_sql),
):
    # Create dummy dataset based on seed and number of rows
    ds_metadata = ADMIN_DATABASE.get_dataset_metadata(query_json.dataset_name)

    ds_df = make_dummy_dataset(
        ds_metadata, query_json.dummy_nb_rows, query_json.dummy_seed
    )
    ds_private_dataset = InMemoryDataset(ds_metadata, ds_df)

    dummy_querier = SmartnoiseSQLQuerier(private_dataset=ds_private_dataset)

    # Catch all non-http exceptions so that the server does not fail.
    try:
        response_df = dummy_querier.query(query_json)

        response = {"query_response": response_df}

    except HTTPException as e:
        raise e
    except Exception as e:
        LOG.info(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)

    # Return response
    return response


@app.post(
    "/estimate_smartnoise_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_smartnoise_cost(
    query_json: SNSQLInpCost = Body(example_smartnoise_sql_cost),
):
    # Catch all non-http exceptions so that the server does not fail.
    try:
        response = QUERY_HANDLER.estimate_cost(
            LIB_SMARTNOISE_SQL,
            query_json,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        LOG.info(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)

    # Return response
    return response


@app.post(
    "/opendp_query", dependencies=[Depends(server_live)], tags=["USER_QUERY"]
)
def opendp_query_handler(
    query_json: OpenDPInp = Body(example_opendp),
    user_name: str = Header(None),
):
    try:
        response = QUERY_HANDLER.handle_query(
            LIB_OPENDP, query_json, user_name
        )
    except HTTPException as he:
        LOG.exception(he)
        raise he
    except Exception as e:
        LOG.exception(e)
        raise HTTPException(500, str(e))

    return response


@app.post(
    "/dummy_opendp_query",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_opendp_query_handler(
    query_json: DummyOpenDPInp = Body(example_dummy_opendp),
):
    # Create dummy dataset based on seed and number of rows
    ds_metadata = ADMIN_DATABASE.get_dataset_metadata(query_json.dataset_name)

    ds_df = make_dummy_dataset(
        ds_metadata, query_json.dummy_nb_rows, query_json.dummy_seed
    )
    ds_private_dataset = InMemoryDataset(ds_metadata, ds_df)
    dummy_querier = OpenDPQuerier(private_dataset=ds_private_dataset)

    # Catch all non-http exceptions so that the server does not fail.
    try:
        response_df = dummy_querier.query(query_json)

        response = {"query_response": response_df}

    except HTTPException as e:
        raise e
    except Exception as e:
        LOG.info(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)

    # Return response
    return response


@app.post(
    "/estimate_opendp_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_opendp_cost(
    query_json: OpenDPInp = Body(example_opendp),
):
    # Catch all non-http exceptions so that the server does not fail.
    try:
        response = QUERY_HANDLER.estimate_cost(
            LIB_OPENDP,
            query_json,
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        LOG.info(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)

    # Return response
    return response


# MongoDB get initial budget query
@app.post(
    "/get_initial_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_initial_budget(
    query_json: GetDbData = Body(example_get_db_data),
    user_name: str = Header(None),
):
    initial_epsilon, initial_delta = ADMIN_DATABASE.get_initial_budget(
        user_name, query_json.dataset_name
    )

    return {"initial_epsilon": initial_epsilon, "initial_delta": initial_delta}


# MongoDB get total spent budget query
@app.post(
    "/get_total_spent_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_total_spent_budget(
    query_json: GetDbData = Body(example_get_db_data),
    user_name: str = Header(None),
):
    (
        total_spent_epsilon,
        total_spent_delta,
    ) = ADMIN_DATABASE.get_total_spent_budget(
        user_name, query_json.dataset_name
    )

    return {
        "total_spent_epsilon": total_spent_epsilon,
        "total_spent_delta": total_spent_delta,
    }


@app.post(
    "/get_remaining_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_remaining_budget(
    query_json: GetDbData = Body(example_get_db_data),
    user_name: str = Header(None),
):
    rem_epsilon, rem_delta = ADMIN_DATABASE.get_remaining_budget(
        user_name, query_json.dataset_name
    )

    return {"remaining_epsilon": rem_epsilon, "remaining_delta": rem_delta}


@app.post(
    "/get_previous_queries",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_user_previous_queries(
    query_json: GetDbData = Body(example_get_db_data),
    user_name: str = Header(None),
):
    previous_queries = ADMIN_DATABASE.get_user_previous_queries(
        user_name, query_json.dataset_name
    )

    return {"previous_queries": previous_queries}


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

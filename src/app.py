from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request

import globals
from mongodb_admin import MongoDB_Admin
from database.utils import database_factory
from dp_queries.dp_logic import QueryHandler
from dp_queries.example_inputs import (
    example_dummy_smartnoise_sql,
    example_get_dataset_metadata,
    example_get_dummy_dataset,
    example_smartnoise_sql,
    example_get_budget,
)
from dp_queries.input_models import (
    DummySNSQLInp,
    GetDatasetMetadata,
    GetDummyDataset,
    SNSQLInp,
    GetBudgetInp,
)
from dp_queries.dp_libraries.smartnoise_sql import SmartnoiseSQLQuerier
from dp_queries.utils import stream_dataframe
from utils.anti_timing_att import anti_timing_att
from utils.config import get_config
from utils.constants import (
    EXISTING_DATASETS,
    INTERNAL_SERVER_ERROR,
    MONGODB_CONTAINER_NAME,
    MONGODB_PORT,
)
from utils.depends import server_live
from utils.dummy_dataset import make_dummy_dataset
from utils.loggr import LOG


# This object holds the server object
app = FastAPI()


@app.on_event("startup")
def startup_event():
    """
    This function is executed once on server startup"""
    LOG.info("Startup message")
    globals.SERVER_STATE["state"].append("Startup event")

    # Load config here
    LOG.info("Loading config")
    globals.SERVER_STATE["message"].append("Loading config")
    globals.CONFIG = get_config()

    # Fill up database if in develop mode ONLY
    if globals.CONFIG.develop_mode:
        LOG.info("!! Develop mode ON !!")
        LOG.info("Creating example user collection")
        # mongo_admin = MongoDB_Admin(
        #     f"mongodb://{MONGODB_CONTAINER_NAME}:{MONGODB_PORT}/"
        # )
        db_port = globals.CONFIG.port
        db_name = globals.CONFIG.db_name
        db_username = globals.CONFIG.username
        db_password = globals.CONFIG.password

        mongo_admin = MongoDB_Admin(
            f'mongodb://{db_username}:{db_password}@mongodb-0.mongodb-headless:{db_port},mongodb-1.mongodb-headless:{db_port}/{db_name}'
        )
        mongo_admin.create_example_users_collection()

        LOG.info("Adding dataset metadata")
        for ds_name in EXISTING_DATASETS:
            # Dirty trick to create a dummy args object.
            def args():
                return None

            args.dataset = ds_name
            mongo_admin.add_metadata(args)

        del mongo_admin

    # Load users, datasets, etc..
    LOG.info("Loading user database")
    globals.SERVER_STATE["message"].append("Loading user database")
    try:
        globals.DATABASE = database_factory(globals.CONFIG.database)
    except Exception as e:
        LOG.exception("Failed at startup:" + str(e))
        globals.SERVER_STATE["state"].append(
            "Loading user database at Startup failed"
        )
        globals.SERVER_STATE["message"].append(str(e))

    LOG.info("Loading query handler")
    globals.SERVER_STATE["message"].append("Loading query handler")
    globals.QUERY_HANDLER = QueryHandler(globals.DATABASE)

    globals.SERVER_STATE["state"].append("Startup completed")
    globals.SERVER_STATE["message"].append("Startup completed")

    # Finally check everything in startup went well and update the state
    globals.check_start_condition()


# A simple hack to hinder the timing attackers
@app.middleware("http")
async def middleware(request: Request, call_next):
    return await anti_timing_att(request, call_next, globals.CONFIG)


# Example implementation for an endpoint
@app.get("/state", tags=["ADMIN_USER"])
async def get_state(user_name: str = Header(None)):
    """
    Returns the current state dict of this server instance.
    """
    return {
        "requested_by": user_name,
        "state": globals.SERVER_STATE,
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
        ds_metadata = globals.DATABASE.get_dataset_metadata(
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
        ds_metadata = globals.DATABASE.get_dataset_metadata(
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
    "/estimate_cost",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def estimate_cost(
    query_json: SNSQLInp = Body(example_smartnoise_sql),
):
    # Catch all non-http exceptions so that the server does not fail.
    try:
        response = globals.QUERY_HANDLER.estimate_cost(
            "smartnoise_sql", query_json
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        LOG.info(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)

    # Return response
    return response


# Smartnoise SQL query
@app.post(
    "/smartnoise_sql",
    dependencies=[Depends(server_live)],
    tags=["USER_QUERY"],
)
def smartnoise_sql_handler(
    query_json: SNSQLInp = Body(example_smartnoise_sql),
    user_name: str = Header(None),
):
    # Catch all non-http exceptions so that the server does not fail.
    try:
        response = globals.QUERY_HANDLER.handle_query(
            "smartnoise_sql", query_json, user_name
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        LOG.info(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)

    # Return response
    return response


# Smartnoise SQL query
@app.post(
    "/dummy_smartnoise_sql",
    dependencies=[Depends(server_live)],
    tags=["USER_DUMMY"],
)
def dummy_smartnoise_sql_handler(
    query_json: DummySNSQLInp = Body(example_dummy_smartnoise_sql),
):
    # Create dummy dataset based on seed and number of rows
    ds_metadata = globals.DATABASE.get_dataset_metadata(
        query_json.dataset_name
    )

    dummy_querier = SmartnoiseSQLQuerier(
        ds_metadata,
        dummy=True,
        dummy_nb_rows=query_json.dummy_nb_rows,
        dummy_seed=query_json.dummy_seed,
    )

    # Catch all non-http exceptions so that the server does not fail.
    try:
        response_df = dummy_querier.query(
            query_json.query_str,
            eps=query_json.epsilon,
            delta=query_json.delta,
        )

        response = {"query_response": response_df.to_dict(orient="tight")}

    except HTTPException as e:
        raise e
    except Exception as e:
        LOG.info(f"Exception raised: {e}")
        raise HTTPException(status_code=500, detail=INTERNAL_SERVER_ERROR)

    # Return response
    return response


# MongoDB get current budget query
@app.post(
    "/get_total_spent_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_total_spent_budget(
    query_json: GetBudgetInp = Body(example_get_budget),
    user_name: str = Header(None),
):
    (
        total_spent_epsilon,
        total_spent_delta,
    ) = globals.DATABASE.get_total_spent_budget(
        user_name, query_json.dataset_name
    )

    return {
        "total_spent_epsilon": total_spent_epsilon,
        "total_spent_delta": total_spent_delta,
    }


# MongoDB get initial budget query
@app.post(
    "/get_initial_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_initial_budget(
    query_json: GetBudgetInp = Body(example_get_budget),
    user_name: str = Header(None),
):
    initial_epsilon, initial_delta = globals.DATABASE.get_initial_budget(
        user_name, query_json.dataset_name
    )

    return {"initial_epsilon": initial_epsilon, "initial_delta": initial_delta}


@app.post(
    "/get_remaining_budget",
    dependencies=[Depends(server_live)],
    tags=["USER_BUDGET"],
)
def get_remaining_budget(
    query_json: GetBudgetInp = Body(example_get_budget),
    user_name: str = Header(None),
):
    rem_epsilon, rem_delta = globals.DATABASE.get_remaining_budget(
        user_name, query_json.dataset_name
    )

    return {"remaining_epsilon": rem_epsilon, "remaining_delta": rem_delta}


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

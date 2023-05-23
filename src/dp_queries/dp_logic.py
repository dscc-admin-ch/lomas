from abc import ABC, abstractmethod
from fastapi import Header, HTTPException

from dp_queries.input_models import BasicModel
import globals
from utils.loggr import LOG


class DPQuerier(ABC):
    """
    Overall query to external DP library
    """

    @abstractmethod
    def __init__(self) -> None:
        """
        Initialise with specific dataset
        """
        pass

    @abstractmethod
    def cost(self, query_str: str, eps: float, delta: float) -> [float, float]:
        """
        Estimate cost of query
        """
        pass

    @abstractmethod
    def query(self, query_str: str, eps: float, delta: float) -> list:
        """
        Does the query and return the response
        """
        pass


def dp_query_logic(
    query_type: str,
    query_json: BasicModel,
    x_oblv_user_name: str = Header(None),
):
    from dp_queries.smartnoise_json.smartnoise_sql import (
        smartnoise_dataset_factory,
    )

    # Query the right dataset with the right query type
    if query_type == "smartnoise_sql":
        dp_querier = smartnoise_dataset_factory(query_json.dataset_name)
    # If other librairies, add dp_querier here.
    # Note: dp_querier must ihnerit from DBQuerier
    else:
        e = f"Query type {query_type} unknown in dp_query_logic"
        LOG.exception(e)
        raise HTTPException(404, str(e))

    # Get cost of the query
    eps_cost, delta_cost = dp_querier.cost(
        query_json.query_str, query_json.epsilon, query_json.delta
    )

    # Check that user may query
    if not globals.USER_DATABASE.may_user_query(x_oblv_user_name):
        e = f"User {x_oblv_user_name} may not query now. Already querying."
        LOG.exception(e)
        raise HTTPException(403, str(e))
    
    # Block access to other queries to user
    globals.USER_DATABASE.set_may_user_query(x_oblv_user_name, False)
    
    # Check that enough budget to to the query
    eps_max_user, delta_max_user = globals.USER_DATABASE.get_max_budget(
        x_oblv_user_name, query_json.dataset_name
    )
    eps_curr_user, delta_curr_user = globals.USER_DATABASE.get_current_budget(
        x_oblv_user_name, query_json.dataset_name
    )

    # If enough budget
    if ((eps_max_user - eps_curr_user) >= eps_cost) and (
        (delta_max_user - delta_curr_user) >= delta_cost
    ):
        # Query
        try:
            response, _ = dp_querier.query(
                query_json.query_str, query_json.epsilon, query_json.delta
            )
        except HTTPException as he:
            LOG.exception(he)
            raise he
        except Exception as e:
            LOG.exception(e)
            raise HTTPException(500, str(e))

        # Deduce budget from user
        globals.USER_DATABASE.update_budget(
            x_oblv_user_name, query_json.dataset_name, eps_cost, delta_cost
        )

        # Add query to db (for archive)
        globals.USER_DATABASE.save_query(
            x_oblv_user_name,
            query_json.dataset_name,
            eps_cost,
            delta_cost,
            query_json.query_str,
        )

    # If not enough budget, do not update nor return response
    else:
        response = {
            "requested_by": x_oblv_user_name,
            "state": f"Not enough budget to perform query. Nothing was done. \
            Current epsilon: {eps_curr_user}, Current delta {delta_curr_user} \
            Max epsilon: {eps_max_user}, Max delta {delta_max_user} ",
        }
    
    # Re-enable user to query
    globals.USER_DATABASE.set_may_user_query(x_oblv_user_name, True)
    
    # Return response
    return response

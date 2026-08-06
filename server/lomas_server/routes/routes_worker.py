from copy import deepcopy
from typing import Annotated

from csvw_eo.metadata_structure import TableMetadata
from fastapi import APIRouter, Depends, Request, Response, Security, status
from fastapi.security import APIKeyHeader

from lomas_core.exceptions import (
    DatasetNotFoundException,
    InternalServerException,
    InvalidQueryException,
    JobNotFoundException,
)
from lomas_core.models.collections import DSInfo, User, UserId
from lomas_core.models.constants import (
    JobStatus,
    LomasHeaders,
)
from lomas_core.models.requests import LomasRequestModel, QueryModel
from lomas_core.models.responses import (
    Job,
    RemainingBudgetResponse,
)
from lomas_server.admin_database.local_database import LocalAdminDatabase
from lomas_server.routes.error_handler import API_ERROR_RESPONSES, model_from_lomas_exception
from lomas_server.routes.utils import get_user_id_from_api_key

router = APIRouter(
    prefix="/w",
    tags=["workers"],
    # All worker routes must have an API key
    dependencies=[Depends(APIKeyHeader(name=LomasHeaders.APIKEY))],
    responses=API_ERROR_RESPONSES,
)


def set_query_result(admin_database: LocalAdminDatabase, job_update: Job) -> None:
    with admin_database.get_db_conn() as conn:
        try:
            job = admin_database.get_job(job_update.uid, conn)

            if not job.status == JobStatus.IN_PROGRESS:
                raise InvalidQueryException(f"Job with uid {job_update.uid} not in progress anymore")

            try:
                # Make sure job did not fail
                if job_update.status == JobStatus.FAILED:
                    return  # Finally still runs!

                # Validate budget
                user = admin_database.get_user(job.requested_by, conn)

                dataset_of_user = user.datasets[job.dataset_name]
                remaining_eps = dataset_of_user.initial_epsilon - dataset_of_user.total_spent_epsilon
                remaining_delta = dataset_of_user.initial_delta - dataset_of_user.total_spent_delta

                if job_update.result is None:
                    raise InternalServerException(f"Job result for job {job_update.uid} is None.")

                if job_update.result.epsilon > remaining_eps or job_update.result.delta > remaining_delta:
                    raise InvalidQueryException(
                        "Not enough budget for this query epsilon remaining "
                        f"{remaining_eps}, delta remaining {remaining_delta}."
                    )

                # Store updated budget
                dataset_of_user.total_spent_epsilon += job_update.result.epsilon
                dataset_of_user.total_spent_delta += job_update.result.delta

                admin_database.replace_user(user, conn)

                # Store job
                admin_database.update_job(job_update, conn)

            except Exception as exc:  # pylint: disable=broad-exception-caught
                # If anything goes bad, just fail the job

                error_model, status_code = model_from_lomas_exception(exc)

                job_update.error = error_model
                job_update.status_code = status_code
                job_update.status = JobStatus.FAILED

                raise exc
            finally:
                # Always update job
                admin_database.update_job(job_update, conn)

            return

        except Exception as e:
            conn.rollback()
            raise e


@router.put("/job")
def update_job(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_api_key)],
    job_update: Job,
) -> None:
    admin_database = request.app.state.admin_database

    if not admin_database.does_job_exist(job_update.uid):
        raise JobNotFoundException(job_update.uid)

    match job_update.query:
        case QueryModel():
            print("adjust cost and more")
            set_query_result(admin_database, job_update)
        case _:  # Cost or dummy
            admin_database.update_job(job_update)

    admin_database.archive_job(job_update.uid)


@router.get("/job/pending")
async def get_next_pending(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_api_key)],
    response: Response,
) -> Job | None:
    admin_database = request.app.state.admin_database
    next_pending = admin_database.get_job_pending()

    if next_pending is None:
        response.status_code = status.HTTP_204_NO_CONTENT
        return None

    update_job = deepcopy(next_pending)
    update_job.status = JobStatus.IN_PROGRESS
    admin_database.update_job(update_job)

    return next_pending


@router.get("/users/{username}")
def get_user_w(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_api_key)],
    username: str,
) -> User:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.get_user(username)


# @router.put("/users/{username}/dataset/budget")
# def update_epsilon_delta_w(
#     request: Request,
#     _: Annotated[UserId, Security(get_user_id_from_api_key)],
#     username: str,
#     body: LomasBudgetRequest,
# ) -> None:
#     db: LocalAdminDatabase = request.app.state.admin_database
#     db.update_budget(username, body.dataset_name, body.epsilon, body.delta)


### 'Proxy' api functions TODO: better
@router.post("/get_remaining_budget")
def get_remaining_budget_w(
    request: Request,
    user_id: Annotated[UserId, Security(get_user_id_from_api_key)],
    query_json: LomasRequestModel,
) -> RemainingBudgetResponse:
    app = request.app
    rem_epsilon, rem_delta = app.state.admin_database.get_remaining_budget(
        user_id.name, query_json.dataset_name
    )
    return RemainingBudgetResponse(remaining_epsilon=rem_epsilon, remaining_delta=rem_delta)


@router.get("/dataset/{dataset_name}/metadata")
def get_dataset_metadata_admin_w(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_api_key)],
    dataset_name: str,
) -> TableMetadata:
    db: LocalAdminDatabase = request.app.state.admin_database

    if not db.does_dataset_exist(dataset_name):
        raise DatasetNotFoundException(dataset_name)

    return db.get_dataset_metadata(dataset_name)


@router.get("/dataset/{dataset_name}")
def get_dataset_w(
    request: Request,
    _: Annotated[UserId, Security(get_user_id_from_api_key)],
    dataset_name: str,
) -> DSInfo:
    db: LocalAdminDatabase = request.app.state.admin_database
    return db.get_dataset(dataset_name)

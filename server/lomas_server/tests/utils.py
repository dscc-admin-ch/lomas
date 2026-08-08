import os
from contextlib import contextmanager
from test.support import sleeping_retry

import httpx2
from fastapi import status
from pydantic import JsonValue

from lomas_core.models.constants import AuthenticationType, JobStatus
from lomas_core.models.exceptions import LomasAPIErrorModel
from lomas_core.models.responses import Job


@contextmanager
def free_pass_env(*, auth_env_key="LOMAS_SERVICE_authenticator__authentication_type"):
    """Enter a context with modified os environment using free_pass authentication."""
    previous_auth = os.getenv(auth_env_key, "")
    os.environ[auth_env_key] = AuthenticationType.FREE_PASS
    try:
        yield
    finally:
        os.environ[auth_env_key] = previous_auth


def wait_for_job(client: httpx2.Client, endpoint: str, headers: dict[str, str] | None = None) -> Job:
    """Periodically query the job endpoint sleeping in between until it completes / times-out."""
    for _ in sleeping_retry(120, error=False):
        job_query = client.get(endpoint, headers=headers).json()
        if job_query["status"] in {JobStatus.COMPLETE, JobStatus.FAILED}:
            return Job.model_validate(job_query)

    raise TimeoutError(f"Job {endpoint} didn't complete in time")


def submit_job_wait(
    client: httpx2.Client, endpoint: str, json: dict[str, JsonValue], headers: dict[str, str] | None = None
) -> Job:
    """Post to a Job-type endpoint and periodically wait for result."""
    query_job_submit = client.post(endpoint, json=json, headers=headers)

    if query_job_submit.status_code != status.HTTP_202_ACCEPTED:
        error = LomasAPIErrorModel.model_validate_json(query_job_submit.content)
        return Job(
            requested_by="",
            dataset_name="",
            query=None,
            status=JobStatus.FAILED,
            status_code=query_job_submit.status_code,
            error=error,
        )

    job_uid = query_job_submit.json()["uid"]
    job = wait_for_job(client, f"/status/{job_uid}", headers=headers)

    return job

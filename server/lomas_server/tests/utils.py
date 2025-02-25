from json import loads
from time import sleep
from typing import Optional, Tuple

from fastapi import status
from httpx import Response

from lomas_core.models.responses import Job


def wait_for_job(client, endpoint, n_retry=100, sleep_sec=0.5) -> Job:
    """Periodically query the job endpoint sleeping in between until it completes / times-out."""
    for _ in range(n_retry):
        job_query = client.get(endpoint).json()

        if job_query["status"] == "complete":
            return Job.model_validate(job_query)

        if (job_err := job_query.get("error")) is not None:
            return Job.model_validate(job_query | {"error": loads(job_err)})

        sleep(sleep_sec)

    raise TimeoutError(f"Job {endpoint} didn't complete in time ({sleep_sec * n_retry})")


def submit_job_wait(client, endpoint, json, headers=None, **kwargs) -> Tuple[Response, Optional[Job]]:
    """Post to a Job-type endpoint and periodically wait for result."""
    query_job_submit = client.post(endpoint, json=json, headers=headers)
    assert query_job_submit.status_code == status.HTTP_202_ACCEPTED

    if query_job_submit.status_code != status.HTTP_202_ACCEPTED:
        return query_job_submit, None

    job_uid = query_job_submit.json()["uid"]
    job = wait_for_job(client, f"/status/{job_uid}", **kwargs)

    return query_job_submit, job

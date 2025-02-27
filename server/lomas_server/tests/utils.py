from json import loads
from test.support import sleeping_retry

from fastapi import status

from lomas_core.models.responses import Job


def wait_for_job(client, endpoint) -> Job:
    """Periodically query the job endpoint sleeping in between until it completes / times-out."""
    for _ in sleeping_retry(75, error=False):
        job_query = client.get(endpoint).json()

        if job_query["status"] == "complete":
            return Job.model_validate(job_query)

        if (job_err := job_query.get("error")) is not None:
            return Job.model_validate(job_query | {"error": loads(job_err)})

    raise TimeoutError(f"Job {endpoint} didn't complete in time")


def submit_job_wait(client, endpoint, json, headers=None) -> Job:
    """Post to a Job-type endpoint and periodically wait for result."""
    query_job_submit = client.post(endpoint, json=json, headers=headers)
    assert query_job_submit.status_code == status.HTTP_202_ACCEPTED

    job_uid = query_job_submit.json()["uid"]
    job = wait_for_job(client, f"/status/{job_uid}")

    return job

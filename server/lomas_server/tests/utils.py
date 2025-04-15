import os
from json import loads
from test.support import sleeping_retry

from fastapi import status

from lomas_core.models.exceptions import LomasServerExceptionTypeAdapter
from lomas_core.models.responses import Job


def wait_for_job(client, endpoint, headers=None) -> Job:
    """Periodically query the job endpoint sleeping in between until it completes / times-out."""
    for _ in sleeping_retry(120, error=False):
        job_query = client.get(endpoint, headers=headers).json()
        if job_query["status"] == "complete":
            return Job.model_validate(job_query)

        if (job_err := job_query.get("error")) is not None:
            return Job.model_validate(job_query | {"error": loads(job_err)})

    raise TimeoutError(f"Job {endpoint} didn't complete in time")


def submit_job_wait(client, endpoint, json, headers=None) -> Job:
    """Post to a Job-type endpoint and periodically wait for result."""
    query_job_submit = client.post(endpoint, json=json, headers=headers)

    if query_job_submit.status_code != status.HTTP_202_ACCEPTED:
        error = LomasServerExceptionTypeAdapter.validate_json(query_job_submit.content)
        return Job(status="failed", status_code=query_job_submit.status_code, error=error)

    job_uid = query_job_submit.json()["uid"]
    job = wait_for_job(client, f"/status/{job_uid}", headers=headers)

    return job


def get_test_dir() -> str:
    """Returns the absolute path of the test directory.

    (Based on the fact that this utils file is placed in the test directory).

    Returns:
        str: The absolute path of the test directory.
    """
    this_file_path = os.path.abspath(__file__)
    test_dir = os.path.dirname(this_file_path)

    return test_dir

import json
import os
from time import sleep
from typing import Optional, Tuple

from fastapi import status
from httpx import Response

from lomas_core.models.responses import Job

ENV_MONGO_INTEGRATION = "LOMAS_TEST_MONGO_INTEGRATION"
ENV_S3_INTEGRATION = "LOMAS_TEST_S3_INTEGRATION"
TRUE_VALUES = ("true", "1", "t")

PENGUIN_COLUMNS = [
    "species",
    "island",
    "bill_length_mm",
    "bill_depth_mm",
    "flipper_length_mm",
    "body_mass_g",
    "sex",
]

PUMS_COLUMNS = ["age", "sex", "educ", "race", "income", "married"]


def mongo_integration_enabled():
    return os.getenv(ENV_MONGO_INTEGRATION, "0").lower() in TRUE_VALUES


def s3_integration_enabled():
    return os.getenv(ENV_S3_INTEGRATION, "0").lower() in TRUE_VALUES


def wait_for_job(client, endpoint, n_retry=50, sleep_sec=0.5) -> Job:
    """Periodically query the job endpoint sleeping in between until it completes / times-out."""
    for i in range(n_retry):
        job_query = client.get(endpoint).json()

        if job_query["status"] == "complete":
            return Job.model_validate(job_query)

        if (job_err := job_query.get("error")) is not None:
            return Job.model_validate(job_query | {"error": json.loads(job_err)})

        sleep(sleep_sec)

    # return Job.model_validate(job_query | {"error": "What the Cinnamon Toast Fuck Is This"})
    raise TimeoutError(f"Job {endpoint} didn't complete in time ({sleep_sec * n_retry})")


def submit_job_wait(
    client, endpoint, json, headers=None, expected_job_status=status.HTTP_202_ACCEPTED, *args, **kwargs
) -> Tuple[Response, Optional[Job]]:
    query_job_submit = client.post(endpoint, json=json, headers=headers)
    assert query_job_submit.status_code == expected_job_status

    if query_job_submit.status_code != status.HTTP_202_ACCEPTED:
        return query_job_submit, None

    job_uid = query_job_submit.json()["uid"]
    job = wait_for_job(client, f"/status/{job_uid}", *args, **kwargs)

    return query_job_submit, job

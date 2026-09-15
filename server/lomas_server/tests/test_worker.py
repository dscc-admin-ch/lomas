from datetime import timedelta
from functools import partial
from pathlib import Path

import anyio
import pytest
from anyio.from_thread import start_blocking_portal
from fastapi import status
from fastapi.testclient import TestClient

from lomas_core.models.constants import AuthenticationType, JobResultStatus
from lomas_core.models.requests_examples import EXAMPLE_OPENDP_POLARS_PLAN
from lomas_core.models.responses import Job
from lomas_server.app import get_full_app
from lomas_server.auth.auth import FreePassAuthenticator
from lomas_server.models.config import ServerConfig
from lomas_server.worker import WorkerConfig, process_message


@pytest.fixture
def config():
    return ServerConfig(authenticator=FreePassAuthenticator(authentication_type=AuthenticationType.FREE_PASS))


@pytest.fixture
def headers():
    user_name = "Dr.Antartica"
    return {
        "Content-type": "application/json",
        "Accept": "*/*",
        "Authorization": f"Bearer {user_name}",
    }


@pytest.fixture
def testdb(config):
    path_prefix = Path(__file__).parent / "test_data"

    config.database.wipe()
    config.database.set_bootstrap(config.bootstrap)

    config.database.add_users_via_yaml(
        yaml_file=(path_prefix / "test_user_collection.yaml"), clean=True, overwrite=False
    )

    config.database.add_datasets_via_yaml(
        # yaml_file=(path_prefix / "test_datasets_with_s3.yaml"),
        yaml_file=(path_prefix / "test_datasets.yaml"),
        clean=True,
        path_prefix=path_prefix,
    )

    yield config.database

    config.database.wipe()


def get_job_status(job_uid, client, headers):
    job_response = client.get(f"/status/{job_uid}", headers=headers)
    assert job_response.status_code == 200
    job = Job.model_validate(job_response.json())
    assert job.uid == job_uid
    return job.status


def test_worker(testdb, config, headers):
    with TestClient(get_full_app(config), headers=headers) as client:
        job_status = partial(get_job_status, client=client, headers=headers)

        response = client.post("/get_dataset_metadata", json={"dataset_name": "PUMS"})
        assert response.status_code == status.HTTP_200_OK

        response = client.post("/opendp_query", json=EXAMPLE_OPENDP_POLARS_PLAN)
        assert response.status_code == 202
        job_uid = Job.model_validate(response.json()).uid

        with start_blocking_portal(name="worker_portal") as portal:
            portal.call(process_message, WorkerConfig(), client, 1)

        assert job_status(job_uid) == JobResultStatus.COMPLETE


def test_worker_timeout(testdb, config, headers):
    job_post_process = lambda *args: print("not sending it back")  # noqa: E731
    database_job_expiry_delay = timedelta(seconds=5)

    config_fast_expiry = config.model_copy(update=dict(database_job_expiry_delay=database_job_expiry_delay))

    with TestClient(get_full_app(config_fast_expiry), headers=headers) as client:
        job_status = partial(get_job_status, client=client, headers=headers)

        response = client.post("/get_dataset_metadata", json={"dataset_name": "PUMS"})
        assert response.status_code == status.HTTP_200_OK

        response = client.post("/opendp_query", json=EXAMPLE_OPENDP_POLARS_PLAN)
        assert response.status_code == 202
        job_uid = Job.model_validate(response.json()).uid

        with start_blocking_portal(name="worker_portal") as portal:
            portal.call(process_message, WorkerConfig(), client, 1, job_post_process)

        # from server: nothing done yet
        assert job_status(job_uid) == JobResultStatus.INCOMPLETE

        # too soon shouldn't get any job
        with start_blocking_portal(name="worker_portal") as portal:
            portal.call(process_message, WorkerConfig(), client, 1)

        assert job_status(job_uid) == JobResultStatus.INCOMPLETE

        # wait for expiry
        client.portal.call(anyio.sleep, database_job_expiry_delay.total_seconds() - 2)
        # now we should get it
        with start_blocking_portal(name="worker_portal") as portal:
            portal.call(process_message, WorkerConfig(), client, 1)

        assert job_status(job_uid) == JobResultStatus.COMPLETE

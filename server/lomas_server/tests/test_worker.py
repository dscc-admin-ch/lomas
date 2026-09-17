import contextlib
from datetime import timedelta
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory

import anyio
import pytest
from anyio.from_thread import start_blocking_portal
from fastapi import status
from fastapi.testclient import TestClient
from returns.result import Success

from lomas_core.models.constants import AuthenticationType, JobResultStatus
from lomas_core.models.requests_examples import EXAMPLE_OPENDP_POLARS_PLAN
from lomas_core.models.responses import Job
from lomas_server.app import get_full_app
from lomas_server.auth.auth import FreePassAuthenticator
from lomas_server.models.config import ServerConfig
from lomas_server.worker import WorkerConfig, worker_loop


@pytest.fixture
def config():
    with TemporaryDirectory(prefix="lomas-db-test-") as tempdir:
        yield ServerConfig(
            database_directory=Path(tempdir),
            authenticator=FreePassAuthenticator(authentication_type=AuthenticationType.FREE_PASS),
        )


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
    return job


@contextlib.contextmanager
def worker_run(client):
    worker_config = WorkerConfig()
    with start_blocking_portal(name="worker_portal") as portal:

        def work_in_thread(**kwargs):
            do_work = partial(worker_loop, worker_config, client, n_steps=1, **kwargs)
            return portal.call(do_work)

        yield work_in_thread


def test_worker(testdb, config, headers):
    with TestClient(get_full_app(config), headers=headers) as client, worker_run(client) as work:
        job_status = partial(get_job_status, client=client, headers=headers)

        response = client.post("/get_dataset_metadata", json={"dataset_name": "PUMS"})
        assert response.status_code == status.HTTP_200_OK

        response = client.post("/opendp_query", json=EXAMPLE_OPENDP_POLARS_PLAN)
        assert response.status_code == 202
        job = Job.model_validate(response.json())

        work()

        assert job_status(job.uid).success()


def test_worker_timeout(testdb, config, headers):
    database_job_expiry_delay = timedelta(seconds=5)

    config_fast_expiry = config.model_copy(update=dict(database_job_expiry_delay=database_job_expiry_delay))

    with TestClient(get_full_app(config_fast_expiry), headers=headers) as client, worker_run(client) as work:
        job_status = partial(get_job_status, client=client, headers=headers)

        response = client.post("/get_dataset_metadata", json={"dataset_name": "PUMS"})
        assert response.status_code == status.HTTP_200_OK

        response = client.post("/opendp_query", json=EXAMPLE_OPENDP_POLARS_PLAN)
        assert response.status_code == 202
        job = Job.model_validate(response.json())

        work(job_post_process=lambda *_: print("not sending it back"))
        start_time = client.portal.call(anyio.current_time)

        # from server: nothing done yet
        assert job_status(job.uid).status == JobResultStatus.INCOMPLETE

        # too soon shouldn't get any job
        client.portal.call(anyio.sleep, 1)
        work()

        assert job_status(job.uid).status == JobResultStatus.INCOMPLETE

        # wait for expiry
        client.portal.call(anyio.sleep_until, start_time + database_job_expiry_delay.total_seconds())
        # now we should get it
        work()

        assert job_status(job.uid).success()

        # simulate late reply
        # with pytest.raises(InvalidQueryException, match=r'Job .* not in progress anymore'):
        work(get_next_job=lambda *arg: Success(job))

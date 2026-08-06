import asyncio
import datetime
import json
import shelve
import sqlite3
import sys
from collections.abc import Callable, Generator
from contextlib import contextmanager, nullcontext
from functools import wraps
from pathlib import Path
from tempfile import SpooledTemporaryFile
from typing import Any, BinaryIO, Concatenate, ParamSpec, TypeVar
from uuid import UUID

import boto3
import yaml
from csvw_eo.metadata_structure import TableMetadata
from fastapi import UploadFile
from filelock import SoftFileLock
from pydantic import Field, HttpUrl

from lomas_core.exceptions import (
    InternalServerException,
)
from lomas_core.models.collections import (
    DatasetOfUser,
    DatasetsCollection,
    DSInfo,
    DSPathAccess,
    DSS3Access,
    User,
    UserCollection,
)
from lomas_core.models.constants import (
    JobStatus,
    PrivateDatabaseType,
    QueryTypes,
    get_lomas_logger,
)
from lomas_core.models.responses import Job
from lomas_server.admin_database.admin_database import (
    AdminDatabase,
)
from lomas_server.admin_database.constants import BudgetDBKey, MiscDBKeys, TopDBKey as TK
from lomas_server.utils.metrics import (
    ADMINDB_DELETE_COUNTER,
    ADMINDB_ERROR_COUNTER,
    ADMINDB_INSERT_COUNTER,
    ADMINDB_QUERY_COUNTER,
    ADMINDB_UPDATE_COUNTER,
)
from lomas_server.utils.span import db_span

if sys.version_info >= (3, 12):
    from typing import override
else:
    from typing_extensions import override


logger = get_lomas_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")
DB = TypeVar("DB", bound="LocalAdminDatabase")


def with_lock(fn: Callable[Concatenate[DB, P], T]) -> Callable[Concatenate[DB, P], T]:
    @wraps(fn)
    def wrapper(self: DB, *args: P.args, **kwargs: P.kwargs) -> T:
        with self.lock:
            return fn(self, *args, **kwargs)

    return wrapper


class LocalAdminDatabase(AdminDatabase):
    """Local Admin database in a single file.

    Database creates three files:
        - admin: shelve database
        - admin.lock: SoftFileLock guarding shelve db
        - jobs.sqlite3: SQLite database for jobs.
    """

    directory: Path

    lock: SoftFileLock = Field(exclude=True, default=None)  # Protects inter-process concurrency.
    asyncio_lock: asyncio.Lock = asyncio.Lock()  # Protects softlock re-entry between concurrent coroutines.

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        if self.directory.exists() and not self.directory.is_dir():
            raise NotADirectoryError(f"{self.directory} exists and is not a directory.")
        self.directory.mkdir(parents=True, exist_ok=True)

        self._shelve_path = self.directory / "admin"
        self._lock_path = self.directory / "admin.lock"
        self._db_path = self.directory / "db.sqlite3"
        self._archives_db_path = self.directory / "archives.sqlite3"
        self._misc_db_path = self.directory / "misc.sqlite3"

        self.lock = SoftFileLock(self._lock_path, is_singleton=True, timeout=10)

        self._set_defaults()

    @contextmanager
    def _sqlite_connection(self, path: Path) -> Generator[sqlite3.Connection]:
        """Creates connection context to sqlite database.

        Yields:
            Generator[sqlite3.Connection]: The connection context.
        """
        conn = sqlite3.connect(path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            with conn as conn:  # commits on success, rolls back on exception
                yield conn
        finally:
            conn.close()

    def get_db_conn(self) -> Generator[sqlite3.Connection]:
        """Creates connection context to sqlite database.

        Yields:
            Generator[sqlite3.Connection]: The connection context.
        """
        return self._sqlite_connection(self._db_path)

    @override
    @with_lock
    def wipe(self) -> None:
        """Wipe database to empty."""
        for f in self.directory.iterdir():
            if f == self._lock_path:
                continue
            if f.is_file():
                f.unlink()

        self._set_defaults()

    @with_lock
    def _set_defaults(self) -> None:
        """Sets the default values for all collections in the database."""
        # create the file if it doesn't exists yet (makes open with flag='r' safe)
        with shelve.open(self._shelve_path, writeback=True) as db:
            # Initialize to empty by default
            db.setdefault(TK.DATASETS, {})
            db.setdefault(TK.METADATA, {})

        self._init_sqlite_dbs()

    def _init_sqlite_dbs(self) -> None:
        """Set defaults for jobs db."""
        with self._sqlite_connection(self._db_path) as conn:
            conn.executescript(
                """
                BEGIN;

                CREATE TABLE IF NOT EXISTS jobs (
                    uid TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    dataset_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    job_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_job_user_name ON jobs(user_name);
                CREATE INDEX IF NOT EXISTS idx_status ON jobs(status);

                """
                # Make sure there are no more than 200 jobs in the db (except for those in progress).
                # Enforce at insertion
                """
                DROP TRIGGER IF EXISTS enforce_num_jobs_on_insert;
                CREATE TRIGGER enforce_num_jobs_on_insert
                AFTER INSERT ON jobs
                WHEN NEW.status != 'in_progress'
                BEGIN
                    DELETE FROM jobs
                    WHERE status != 'in_progress'
                    AND started_at IN (
                        SELECT started_at FROM jobs
                        WHERE status != 'in_progress'
                        ORDER BY started_at DESC
                        LIMIT -1 OFFSET 200 -- Keep the 200 newest completed jobs
                    );
                END;

                """
                # Enforce at update
                """
                DROP TRIGGER IF EXISTS enforce_num_jobs_on_update;
                CREATE TRIGGER enforce_num_jobs_on_update
                AFTER UPDATE OF status ON jobs
                WHEN NEW.status != 'in_progress'
                BEGIN
                    DELETE FROM jobs
                    WHERE status != 'in_progress'
                    AND started_at IN (
                        SELECT started_at FROM jobs
                        WHERE status != 'in_progress'
                        ORDER BY started_at DESC
                        LIMIT -1 OFFSET 200
                    );
                END;
                """
                # User table
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_name TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    may_query INTEGER NOT NULL,
                    admin INTEGER NOT NULL,
                    user_json TEXT NOT NULL
                );

                COMMIT;
                """
            )

        with self._sqlite_connection(self._archives_db_path) as conn:
            conn.executescript(
                """
                BEGIN;
                CREATE TABLE IF NOT EXISTS archives (
                    uid TEXT PRIMARY KEY,
                    user_name TEXT NOT NULL,
                    dataset_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    archived_at TEXT,
                    job_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_job_user_name ON archives(user_name);
                CREATE INDEX IF NOT EXISTS idx_job_dataset_name ON archives(dataset_name);
                CREATE INDEX IF NOT EXISTS idx_jobs_user_dataset ON archives(user_name, dataset_name);
                COMMIT;
                """
            )

        with self._sqlite_connection(self._misc_db_path) as conn:
            conn.executescript(
                f"""
                BEGIN;
                CREATE TABLE IF NOT EXISTS misc (
                    name TEXT PRIMARY KEY,
                    value TEXT NULL,
                    disabled INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO misc (name, value, disabled) VALUES ('{MiscDBKeys.BOOTSTRAP:s}', NULL, 0);
                COMMIT;
                """
            )

    # Jobs
    ###########################################################################

    @override
    @db_span("db.does_job_exist", table="admin-db")
    def does_job_exist(self, uid: UUID) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "does_job_exist"})
        with self._sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM jobs WHERE uid = ?", (str(uid),)).fetchone()
        return row is not None

    @override
    @db_span("db.get_job", table="admin-db")
    def get_job(self, uid: UUID, conn: Generator[sqlite3.Connection] | None = None) -> Job:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_job"})

        with self._sqlite_connection(self._db_path) if conn is None else nullcontext(conn) as conn:
            row = conn.execute("SELECT job_json FROM jobs WHERE uid = ?", (str(uid),)).fetchone()

        if row is None:
            raise KeyError(f"No job with uid {uid}")

        return Job.model_validate_json(row[0])

    @db_span("db.get_job_pending", table="admin-db")
    def get_job_pending(self) -> Job | None:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_job_pending"})

        with self._sqlite_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT job_json FROM jobs WHERE status = ?", (str(JobStatus.PENDING),)
            ).fetchone()

        if row is None:
            return None

        return Job.model_validate_json(row[0])

    @override
    @db_span("db.put_job", table="admin-db")
    def put_job(self, job: Job) -> None:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "put_job"})
        with self._sqlite_connection(self._db_path) as conn:
            try:
                conn.execute(
                    "INSERT INTO jobs "
                    "(uid, user_name, dataset_name, status, started_at, job_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(job.uid),
                        job.requested_by,
                        job.dataset_name,
                        job.status,
                        datetime.datetime.now(datetime.UTC),
                        job.model_dump_json(),
                    ),
                )
            except sqlite3.IntegrityError as e:
                raise KeyError(f"Job with uid {job.uid} already exists.") from e

    @override
    @db_span("db.update_job", table="admin-db")
    def update_job(
        self, job_update: Job, conn: Generator[sqlite3.Connection, None, None] | None = None
    ) -> None:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "update_job"})

        uid = job_update.uid
        job = self.get_job(uid, conn)

        # Does not perform a deep merge, but not required here.
        merged_data = job.model_dump() | job_update.model_dump(exclude_unset=True)
        merged_job = Job.model_validate(merged_data)

        with self._sqlite_connection(self._db_path) if conn is None else nullcontext(conn) as conn:
            cursor = conn.execute(
                """
                UPDATE jobs
                SET
                    status = ?,
                    job_json = ?
                WHERE uid = ?;
                """,
                (merged_job.status, merged_job.model_dump_json(), str(merged_job.uid)),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"No job with uid {job_update.uid}")

    # @override
    @db_span("db.set_query_result", table="admin-db")
    def set_query_result(self, job_update: Job) -> None:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "set_query_result"})

    # Archives
    ###########################################################################

    @override
    @db_span("db.archive_job", table="admin-db")
    def archive_job(self, uid: UUID) -> None:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "archive_job"})
        job = self.get_job(uid)

        # Ignore cost and dummy queries
        if job.query is not None and job.query.request_type == QueryTypes.QUERY:
            with self._sqlite_connection(self._archives_db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO archives "
                    "(uid, user_name, dataset_name, status, archived_at, job_json) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        str(job.uid),
                        job.requested_by,
                        job.dataset_name,
                        job.status,
                        datetime.datetime.now(datetime.UTC),
                        job.model_dump_json(),
                    ),
                )

    @override
    @db_span("db.get_user_queries", table="admin-db")
    def get_user_queries(self, username: str) -> list[Job]:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_user_queries"})
        with self._sqlite_connection(self._archives_db_path) as conn:
            rows = conn.execute(
                "SELECT job_json FROM archives WHERE user_name = ? ORDER BY archived_at", (username,)
            ).fetchall()

        return [Job.model_validate_json(row[0]) for row in rows]

    @override
    @db_span("db.get_user_dataset_queries", table="admin-db")
    def get_user_dataset_queries(
        self,
        user_name: str,
        dataset_name: str,
    ) -> list[Job]:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_user_dataset_queries"})

        with self._sqlite_connection(self._archives_db_path) as conn:
            rows = conn.execute(
                "SELECT job_json FROM archives WHERE user_name = ? AND dataset_name = ? ORDER BY archived_at",
                (user_name, dataset_name),
            ).fetchall()

        return [Job.model_validate_json(row[0]) for row in rows]

    # Users
    ###########################################################################

    def load_users_collection(self, users: list[User], overwrite: bool) -> None:
        with self._sqlite_connection(self._db_path) as conn:
            if overwrite:
                for user in users:
                    conn.execute(
                        "INSERT OR REPLACE INTO users "
                        "(user_name, email, may_query, admin, user_json) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            user.id.name,
                            user.id.email,
                            int(user.may_query),
                            int(user.admin),
                            user.model_dump_json(),
                        ),
                    )
            else:
                for user in users:
                    try:
                        conn.execute(
                            "INSERT INTO users "
                            "(user_name, email, may_query, admin, user_json) "
                            "VALUES (?, ?, ?, ?, ?)",
                            (
                                user.id.name,
                                user.id.email,
                                int(user.may_query),
                                int(user.admin),
                                user.model_dump_json(),
                            ),
                        )
                    except sqlite3.IntegrityError as e:
                        # Because we are in the same context, all previous inserts will be rolled back
                        raise KeyError(f"User with name {user.id.name} already exists.") from e

    def users(self) -> list[User]:
        with self._sqlite_connection(self._db_path) as conn:
            rows = conn.execute("SELECT user_json FROM users").fetchall()
            return [User.model_validate_json(row[0]) for row in rows]

    def get_user(self, user_name: str, conn: Generator[sqlite3.Connection] | None = None) -> User:
        with self._sqlite_connection(self._db_path) if conn is None else nullcontext(conn) as conn:
            row = conn.execute("SELECT user_json FROM users WHERE user_name = ?", (user_name,)).fetchone()

            if row is None:
                raise KeyError(f"No user with name {user_name}.")

            return User.model_validate_json(row[0])

    def replace_user(self, user: User, conn: Generator[sqlite3.Connection] | None = None) -> None:
        with self._sqlite_connection(self._db_path) if conn is None else nullcontext(conn) as conn:
            cursor = conn.execute(
                """
                UPDATE users
                SET
                    email = ?,
                    may_query = ?,
                    admin = ?,
                    user_json = ?
                WHERE user_name = ?;
                """,
                (user.id.email, user.may_query, user.admin, user.model_dump_json(), user.id.name),
            )

            if cursor.rowcount == 0:
                raise KeyError(f"No user with name {user.id.name}")

    @db_span("db.add_dataset_to_user", table="admin-db")
    def add_dataset_to_user(self, username: str, dataset_name: str, epsilon: float, delta: float) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "add_dataset_to_user"})
        user = self.get_user(username)
        ds = DatasetOfUser(dataset_name=dataset_name, initial_epsilon=epsilon, initial_delta=delta)
        user.datasets = user.datasets | {dataset_name: ds}
        self.replace_user(user)

    @db_span("db.del_dataset_to_user", table="admin-db")
    def del_dataset_to_user(self, username: str, dataset_name: str) -> None:
        ADMINDB_DELETE_COUNTER.add(1, {"operation": "del_dataset_to_user"})
        user = self.get_user(username)
        del user.datasets[dataset_name]
        self.replace_user(user)

    @db_span("db.add_users_via_yaml", table="admin-db")
    def add_users_via_yaml(
        self, yaml_file: Path | BinaryIO | SpooledTemporaryFile, clean: bool, overwrite: bool
    ) -> None:
        """Add all users from yaml file to the user collection.

        Args:
            yaml_file (Path): a path to the YAML file location
            clean (bool): boolean flag
                True if drop current user collection
                False if keep current user collection
            overwrite (bool): boolean flag
                True if already existing users are overwritten
                False if raise KeyError if user already exists

        Raises:
            KeyError: Stops and raises if any of the users already exists.

        Returns:
            None
        """
        if clean:
            self.drop_collection(TK.USERS)

        # Load yaml data and insert it
        match yaml_file:
            case Path():
                yaml_dict = yaml.safe_load(yaml_file.resolve().open(encoding="utf-8"))
            case BinaryIO() | SpooledTemporaryFile():
                yaml_dict = yaml.safe_load(yaml_file)
        self.load_users_collection(UserCollection(**yaml_dict).users, overwrite=overwrite)

    @db_span("db.put_user", table="admin-db")
    def put_user(self, user: User) -> None:
        """Add new user in users collection with default values for all fields.

        Args:
            user (User): user to be added

        Raises:
            ValueError: If the username already exists.

        Returns:
            None
        """
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "put_user"})

        with self._sqlite_connection(self._db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT into users (user_name, email, may_query, admin, user_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user.id.name, user.id.email, user.may_query, user.admin, user.model_dump_json()),
                )
            except sqlite3.IntegrityError as e:
                raise KeyError(f"User with name {user.id.name} already exists.") from e

    @db_span("db.del_user", table="admin-db")
    def del_user(self, user_name: str) -> None:
        ADMINDB_DELETE_COUNTER.add(1, {"operation": "del_user"})
        with self._sqlite_connection(self._db_path) as conn:
            conn.execute("DELETE FROM users WHERE user_name = ?", (user_name,))

    @override
    @db_span("db.does_user_exist", table="admin-db")
    def does_user_exist(self, user_name: str) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "does_user_exist"})
        with self._sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM users WHERE user_name = ?", (user_name,)).fetchone()

            return row is not None

    @override
    @db_span("db.is_user_admin", table="admin-db")
    def is_user_admin(self, user_name: str) -> bool:
        with self._sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT admin FROM users WHERE user_name = ?", (user_name,)).fetchone()

            if row is None:
                raise KeyError(f"No user with name {user_name}")

            return bool(row[0])

    @override
    @db_span("db.has_user_access_to_dataset", table="admin-db")
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "has_user_access_to_dataset"})
        user = self.get_user(user_name)
        return dataset_name in user.datasets

    @override
    @db_span("db.get_epsilon_or_delta", table="admin-db")
    def get_epsilon_or_delta(self, user_name: str, dataset_name: str, parameter: BudgetDBKey) -> float:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_epsilon_or_delta"})
        user = self.get_user(user_name)
        return getattr(user.datasets[dataset_name], parameter)

    @override
    @db_span("db.update_epsilon_or_delta", table="admin-db")
    def update_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: BudgetDBKey,
        spent_value: float,
    ) -> None:
        ADMINDB_UPDATE_COUNTER.add(1, {"operation": "update_epsilon_or_delta"})
        user = self.get_user(user_name)
        new_value = getattr(user.datasets[dataset_name], parameter) + spent_value
        setattr(user.datasets[dataset_name], parameter, new_value)
        self.replace_user(user)

    @db_span("db.set_epsilon_or_delta", table="admin-db")
    def set_epsilon_or_delta(
        self,
        user_name: str,
        dataset_name: str,
        parameter: BudgetDBKey,
        value: float,
    ) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "set_epsilon_or_delta"})
        user = self.get_user(user_name)
        setattr(user.datasets[dataset_name], parameter, value)
        self.replace_user(user)

    # Datasets
    ###########################################################################

    @with_lock
    def load_dataset_collection(self, datasets: list[DSInfo], path_prefix: Path) -> None:
        with shelve.open(self._shelve_path, writeback=True) as db:
            # Step 1: add datasets
            new_datasets = {}
            for ds in datasets:
                # Overwrite path
                if isinstance(ds.dataset_access, DSPathAccess):
                    match ds.dataset_access.path:
                        case HttpUrl():
                            pass
                        case Path():
                            ds.dataset_access.path = path_prefix / ds.dataset_access.path
                if isinstance(ds.metadata_access, DSPathAccess):
                    match ds.metadata_access.path:
                        case HttpUrl():
                            pass
                        case Path():
                            ds.metadata_access.path = path_prefix / ds.metadata_access.path

                # Fill datasets_list
                new_datasets[ds.dataset_name] = ds.model_dump()

            # Add dataset collection
            if new_datasets:
                db[TK.DATASETS].update(new_datasets)

            db[TK.METADATA] = {}
            # Step 2: add metadata collections (one metadata per dataset)
            for ds in datasets:
                dataset_name = ds.dataset_name
                metadata_access = ds.metadata_access

                match metadata_access:
                    case DSPathAccess():
                        with metadata_access.path.open("r", encoding="utf-8") as f:
                            metadata_dict = json.load(f)

                    case DSS3Access():
                        client = boto3.client(
                            "s3",
                            endpoint_url=str(metadata_access.endpoint_url),
                            aws_access_key_id=metadata_access.access_key_id,
                            aws_secret_access_key=metadata_access.secret_access_key,
                        )
                        response = client.get_object(
                            Bucket=metadata_access.bucket,
                            Key=metadata_access.key,
                        )
                        try:
                            metadata_dict = json.loads(response["Body"].read())
                        except json.JSONDecodeError as e:
                            ADMINDB_ERROR_COUNTER.add(1, {"operation": "json_decode_error"})
                            raise e

                    case _:
                        ADMINDB_ERROR_COUNTER.add(1, {"operation": "metadata_db_type_error"})
                        raise InternalServerException(
                            f"Unknown metadata_db_type PrivateDatabaseType: {metadata_access.database_type}"
                        )
                db[TK.METADATA][dataset_name] = TableMetadata.from_dict(metadata_dict).model_dump()
                logger.info(f"Added metadata of {dataset_name} dataset.")

    @with_lock
    def datasets(self) -> list[DSInfo]:
        with shelve.open(self._shelve_path, flag="r") as db:
            return list(map(DSInfo.model_validate, db.get(TK.DATASETS, {}).values()))

    @db_span("db.add_datasets_via_yaml", table="admin-db")
    @with_lock
    def add_datasets_via_yaml(
        self,
        yaml_file: Path | BinaryIO | SpooledTemporaryFile,
        clean: bool,
        path_prefix: Path = Path(),
    ) -> None:
        """Set all database types to datasets in dataset collection based.

        on yaml file.

        Args:
            yaml_file (Path|BinaryIO|SpooledTemporaryFile): path to the YAML file location
            clean (bool): Whether to clean the collection before adding.
            path_prefix (Path, optional): Prefix to add to all file paths. Defaults to empty Path.

        Raises:
            ValueError: If there are errors in the YAML file format.

        Returns:
            None
        """
        if clean:
            self.drop_collection("datasets")

        match yaml_file:
            case Path():
                yaml_dict = yaml.safe_load(yaml_file.resolve().open(encoding="utf-8"))
            case BinaryIO() | SpooledTemporaryFile():
                yaml_dict = yaml.safe_load(yaml_file)
        self.load_dataset_collection(DatasetsCollection(**yaml_dict).datasets, path_prefix)

    @db_span("db.add_dataset", table="admin-db")
    @with_lock
    def add_dataset(
        self,
        dataset_name: str,
        database_type: str,
        metadata_database_type: str,
        dataset_path: str | None = "",
        metadata_path: str = "",
        bucket: str | None = "",
        key: str | None = "",
        endpoint_url: str | None = "",
        credentials_name: str | None = "",
        metadata_bucket: str | None = "",
        metadata_key: str | None = "",
        metadata_endpoint_url: str | None = "",
        metadata_access_key_id: str | None = "",
        metadata_secret_access_key: str | None = "",
        metadata_credentials_name: str | None = "",
    ) -> None:
        """Set a database type to a dataset in dataset collection.

        Args:
            dataset_name (str): Dataset name
            database_type (str): Type of the database
            metadata_database_type (str): Metadata database type

            dataset_path (str): Path to the dataset (for local db type)
            metadata_path (str): Path to metadata (for local db type)

            bucket (str): S3 bucket name
            key (str): S3 key
            endpoint_url (str): S3 endpoint URL
            credentials_name (str): The name of the credentials in the\
                server config to retrieve the dataset from S3 storage.
            metadata_bucket (str): Metadata S3 bucket name
            metadata_key (str): Metadata S3 key
            metadata_endpoint_url (str): Metadata S3 endpoint URL
            metadata_access_key_id (str): Metadata AWS access key ID
            metadata_secret_access_key (str): Metadata AWS secret access key
            metadata_credentials_name (str): The name of the credentials in the\
                server config for retrieving the metadata.

        Raises:
            ValueError: If the dataset already exists
                        or if the database type is unknown.

        Returns:
            None
        """
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "add_dataset"})
        # Step 1: Build dataset
        dataset: dict[str, Any] = {"dataset_name": dataset_name}

        dataset_access: dict[str, Any] = {
            "database_type": database_type,
        }

        if database_type == PrivateDatabaseType.PATH:
            if dataset_path is None:
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "datasetpath_error"})
                raise ValueError("Dataset path not set.")
            dataset_access["path"] = dataset_path
        elif database_type == PrivateDatabaseType.S3:
            dataset_access["bucket"] = bucket
            dataset_access["key"] = key
            dataset_access["endpoint_url"] = endpoint_url
            dataset_access["credentials_name"] = credentials_name
        else:
            ADMINDB_ERROR_COUNTER.add(1, {"operation": "database_type_error"})
            raise ValueError(f"Unknown database type {database_type}")

        dataset["dataset_access"] = dataset_access

        # Step 2: Build metadata
        metadata_access: dict[str, Any] = {"database_type": metadata_database_type}
        if metadata_database_type == PrivateDatabaseType.PATH:
            # Store metadata to metadata collection
            metadata_dict = json.loads(Path(metadata_path).resolve().read_text(encoding="utf-8"))
            metadata_access["path"] = metadata_path

        elif metadata_database_type == PrivateDatabaseType.S3:
            client = boto3.client(
                "s3",
                endpoint_url=metadata_endpoint_url,
                aws_access_key_id=metadata_access_key_id,
                aws_secret_access_key=metadata_secret_access_key,
            )
            response = client.get_object(Bucket=metadata_bucket, Key=metadata_key)
            try:
                metadata_dict = json.loads(response["Body"].read().decode("utf-8"))
            except yaml.YAMLError as e:
                raise e

            metadata_access["bucket"] = metadata_bucket
            metadata_access["key"] = metadata_key
            metadata_access["endpoint_url"] = metadata_endpoint_url
            metadata_access["credentials_name"] = metadata_credentials_name

        else:
            ADMINDB_ERROR_COUNTER.add(1, {"operation": "metadata_db_type_error"})
            raise ValueError(f"Unknown database type {metadata_database_type}")

        dataset["metadata_access"] = metadata_access

        # Step 3: Validate
        ds_info = DSInfo.model_validate(dataset)
        validated_dataset = ds_info.model_dump()
        validated_metadata = TableMetadata.from_dict(metadata_dict).model_dump()

        # Step 4: Insert into db
        with shelve.open(self._shelve_path, writeback=True) as db:
            db[TK.DATASETS][ds_info.dataset_name] = validated_dataset
            db[TK.METADATA] = db.get(TK.METADATA, {}) | {dataset_name: validated_metadata}
            db.sync()

    @db_span("db.delete_dataset", table="admin-db")
    @with_lock
    def del_dataset(self, dataset_name: str) -> None:
        ADMINDB_DELETE_COUNTER.add(1, {"operation": "delete_dataset"})
        with shelve.open(self._shelve_path, writeback=True) as db:
            del db[TK.DATASETS][dataset_name]

    @override
    @db_span("db.does_dataset_exist", table="admin-db")
    @with_lock
    def does_dataset_exist(self, dataset_name: str) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "does_dataset_exist"})
        return dataset_name in map(lambda ds: ds.dataset_name, self.datasets())

    @override
    @db_span("db.get_dataset", table="admin-db")
    @with_lock
    def get_dataset(self, dataset_name: str) -> DSInfo:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_dataset"})
        with shelve.open(self._shelve_path, flag="r") as db:
            dataset = db[TK.DATASETS][dataset_name]
            return DSInfo.model_validate(dataset)

    @override
    @db_span("db.get_dataset_metadata", table="admin-db")
    @with_lock
    def get_dataset_metadata(self, dataset_name: str) -> TableMetadata:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_dataset_metadata"})
        with shelve.open(self._shelve_path, flag="r") as db:
            metadata = db.get(TK.METADATA, {}).get(dataset_name)
            return TableMetadata.model_validate(metadata)

    @db_span("db.set_dataset_metadata", table="admin-db")
    @with_lock
    def set_dataset_metadata(self, dataset_name: str, json_file: UploadFile) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "set_dataset_metadata"})
        json_file.seek(0)
        content = json_file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        metadata_dict = json.loads(content)
        validated_metadata = TableMetadata.from_dict(metadata_dict).model_dump()
        with shelve.open(self._shelve_path, writeback=True) as db:
            db[TK.METADATA] = db.get(TK.METADATA, {}) | {dataset_name: validated_metadata}

    # Other
    ###########################################################################

    @db_span("db.drop_collection", table="admin-db")
    @with_lock
    def drop_collection(self, collection: str) -> None:
        ADMINDB_DELETE_COUNTER.add(1, {"operation": "drop_collection"})
        with shelve.open(self._shelve_path, writeback=True) as db:
            if collection in db:
                del db[collection]

        if collection == TK.USERS:
            with self._sqlite_connection(self._db_path) as conn:
                conn.execute("DELETE from users")

        self._set_defaults()

    @override
    def set_bootstrap(self, bootstrap: str) -> None:
        with self._sqlite_connection(self._misc_db_path) as conn:
            conn.execute(
                "UPDATE misc SET value = ?, disabled = ? WHERE name = ?",
                (bootstrap, int(False), MiscDBKeys.BOOTSTRAP),
            )

    @override
    def get_bootstrap(self) -> str | None:
        with self._sqlite_connection(self._misc_db_path) as conn:
            row = conn.execute("SELECT value FROM misc WHERE name = ?", (MiscDBKeys.BOOTSTRAP,)).fetchone()
            match row:
                case (bootstrap_key, *_):
                    return bootstrap_key
                case None:
                    return None
                case _:
                    raise InternalServerException("Invalid Query Returns")

    @override
    def set_bootstrap_disabled(self, bootstrap_disabled: bool = True) -> None:
        with self._sqlite_connection(self._misc_db_path) as conn:
            conn.execute(
                "UPDATE misc SET disabled = ? WHERE name = ?",
                (int(bootstrap_disabled), MiscDBKeys.BOOTSTRAP),
            )

    @override
    def get_bootstrap_disabled(self) -> bool:
        with self._sqlite_connection(self._misc_db_path) as conn:
            row = conn.execute("SELECT disabled FROM misc WHERE name = ?", (MiscDBKeys.BOOTSTRAP,)).fetchone()
            match row:
                case (disabled_int, *_):
                    return bool(disabled_int)
                case None:
                    return False
                case _:
                    raise InternalServerException("Invalid Query Returns")

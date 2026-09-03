import io
import json
import sqlite3
import zipfile
from collections.abc import Generator
from contextlib import AbstractContextManager, closing, contextmanager, nullcontext
from datetime import UTC, datetime
from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryDirectory
from typing import Any, BinaryIO, override
from uuid import UUID

import boto3
import yaml
from csvw_eo.metadata_structure import TableMetadata
from fastapi import UploadFile
from pydantic import HttpUrl

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
from lomas_core.models.responses import Budget, Job
from lomas_server.admin_database.admin_database import (
    AdminDatabase,
)
from lomas_server.admin_database.constants import BudgetDBKey, MiscDBKeys, TopDBKey as TK
from lomas_server.utils.metrics import (
    ADMINDB_DELETE_COUNTER,
    ADMINDB_ERROR_COUNTER,
    ADMINDB_INSERT_COUNTER,
    ADMINDB_QUERY_COUNTER,
)
from lomas_server.utils.span import db_span

logger = get_lomas_logger(__name__)


@contextmanager
def _sqlite_connection(path: Path) -> Generator[sqlite3.Connection]:
    """Creates connection context to sqlite database.

    Yields:
        Generator[sqlite3.Connection]: The connection context.
    """
    # autocommit = False
    # - sqlite3 ensures that a transaction is always open, so connect(), Connection.commit(), and Connection.rollback() will implicitly open a new transaction
    #     (immediately after closing the pending one, for the latter two). sqlite3 uses BEGIN DEFERRED statements when opening transactions.
    # - Transactions should be committed explicitly using commit().
    # - Transactions should be rolled back explicitly using rollback().
    # - An implicit rollback is performed if the database is close()-ed with pending changes.
    with closing(sqlite3.connect(path, timeout=30, autocommit=False)) as conn:
        conn.executescript("COMMIT;PRAGMA journal_mode=WAL;PRAGMA busy_timeout=30000")
        yield conn
        ### Connection Context exits:
        # If the body of the with statement finishes without exceptions, the transaction is committed.
        #   If this commit fails, or if the body of the with statement raises an uncaught exception, the transaction is rolled back.
        #   A new transaction is implicitly opened after committing or rolling back.
        # If there is no open transaction upon leaving the body of the with statement, the context manager does nothing.
        ### Closing Context exits:
        # Implicit rollback on pending changes


class LocalAdminDatabase(AdminDatabase):
    """Local Admin database in a single file.

    Database creates three files:
        - admin: shelve database
        - admin.lock: SoftFileLock guarding shelve db
        - jobs.sqlite3: SQLite database for jobs.
    """

    directory: Path

    def __init__(self, directory: Path) -> None:
        self.directory = directory
        if self.directory.exists() and not self.directory.is_dir():
            raise NotADirectoryError(f"{self.directory} exists and is not a directory.")
        self.directory.mkdir(parents=True, exist_ok=True)

        self._db_path = self.directory / "db.sqlite3"
        self._archives_db_path = self.directory / "archives.sqlite3"

        self._init_sqlite_dbs()

    def get_db_conn(self) -> AbstractContextManager[sqlite3.Connection]:
        """Creates connection context to sqlite database.

        Yields:
            Generator[sqlite3.Connection]: The connection context.
        """
        return _sqlite_connection(self._db_path)

    @override
    def wipe(self) -> None:
        """Wipe database to empty."""
        for collection in TK:
            self.drop_collection(collection)

    def _init_sqlite_dbs(self) -> None:
        """Set defaults for jobs db."""
        with _sqlite_connection(self._db_path) as conn:
            conn.executescript(
                """
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
                """
                # Dataset table # TODO metadata access null or not null
                """
                CREATE TABLE IF NOT EXISTS datasets (
                    dataset_name TEXT PRIMARY KEY,
                    dataset_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                """
                # Misc table
                f"""
                CREATE TABLE IF NOT EXISTS misc (
                    name TEXT PRIMARY KEY,
                    value TEXT NULL,
                    disabled INTEGER NOT NULL
                );
                INSERT OR IGNORE INTO misc (name, value, disabled) VALUES ('{MiscDBKeys.BOOTSTRAP:s}', NULL, 0);
                """
            )

        with _sqlite_connection(self._archives_db_path) as conn:
            conn.executescript(
                """
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
                """
            )

    # Jobs
    ###########################################################################

    @override
    @db_span("db.does_job_exist", table="admin-db")
    def does_job_exist(self, uid: UUID) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "does_job_exist"})
        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM jobs WHERE uid = ?", (str(uid),)).fetchone()
        return row is not None

    @override
    @db_span("db.get_job", table="admin-db")
    def get_job(self, uid: UUID, current_conn: sqlite3.Connection | None = None) -> Job:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_job"})

        with _sqlite_connection(self._db_path) if current_conn is None else nullcontext(current_conn) as conn:
            row = conn.execute("SELECT job_json FROM jobs WHERE uid = ?", (str(uid),)).fetchone()

        if row is None:
            ADMINDB_ERROR_COUNTER.add(1, {"operation": "key-error-user"})
            raise KeyError(f"No job with uid {uid}")

        return Job.model_validate_json(row[0])

    @override
    @db_span("db.get_job_pending", table="admin-db")
    def get_job_pending(self) -> Job | None:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_job_pending"})

        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT job_json FROM jobs WHERE status = ? ORDER BY started_at LIMIT 1",
                (str(JobStatus.PENDING),),
            ).fetchone()

        if row is None:
            return None

        return Job.model_validate_json(row[0])

    @override
    @db_span("db.put_job", table="admin-db")
    def put_job(self, job: Job) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "put_job"})
        with _sqlite_connection(self._db_path) as conn:
            try:
                conn.execute(
                    "INSERT INTO jobs "
                    "(uid, user_name, dataset_name, status, started_at, job_json) "
                    "VALUES (?, ?, ?, ?, 'now', ?)",
                    (
                        str(job.uid),
                        job.requested_by,
                        job.dataset_name,
                        job.status,
                        job.model_dump_json(),
                    ),
                )
            except sqlite3.IntegrityError as e:
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "job-key-error"})
                raise KeyError(f"Job with uid {job.uid} already exists.") from e

    @override
    @db_span("db.update_job", table="admin-db")
    def update_job(self, job_update: Job, current_conn: sqlite3.Connection | None = None) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "update_job"})

        uid = job_update.uid
        job = self.get_job(uid, current_conn)

        # Does not perform a deep merge, but not required here.
        merged_data = job.model_dump() | job_update.model_dump(exclude_unset=True)
        merged_job = Job.model_validate(merged_data)

        with _sqlite_connection(self._db_path) if current_conn is None else nullcontext(current_conn) as conn:
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
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "job_key_error"})
                raise KeyError(f"No job with uid {job_update.uid}")

    # Archives
    ###########################################################################

    @override
    @db_span("db.archive_job", table="admin-db")
    def archive_job(self, uid: UUID) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "archive_job"})
        job = self.get_job(uid)

        # Ignore cost and dummy queries
        if job.query is not None and job.query.request_type == QueryTypes.QUERY:
            with _sqlite_connection(self._archives_db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO archives "
                    "(uid, user_name, dataset_name, status, archived_at, job_json) "
                    "VALUES (?, ?, ?, ?, 'now', ?)",
                    (
                        str(job.uid),
                        job.requested_by,
                        job.dataset_name,
                        job.status,
                        job.model_dump_json(),
                    ),
                )

    @override
    @db_span("db.get_user_queries", table="admin-db")
    def get_user_queries(self, username: str) -> list[Job]:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_user_queries"})
        with _sqlite_connection(self._archives_db_path) as conn:
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

        with _sqlite_connection(self._archives_db_path) as conn:
            rows = conn.execute(
                "SELECT job_json FROM archives WHERE user_name = ? AND dataset_name = ? ORDER BY archived_at",
                (user_name, dataset_name),
            ).fetchall()

        return [Job.model_validate_json(row[0]) for row in rows]

    # Users
    ###########################################################################

    def load_users_collection(self, users: list[User], overwrite: bool) -> None:
        """Loads the list of Users into the database.

        Set overwrite to true to ignore existing users and overwrite
        """
        with _sqlite_connection(self._db_path) as conn:
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
                        ADMINDB_ERROR_COUNTER.add(1, {"operation": "user_key_error"})
                        raise KeyError(f"User with name {user.id.name} already exists.") from e

    @override
    @db_span("db.users", table="admin-db")
    def users(self) -> list[User]:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "users"})
        with _sqlite_connection(self._db_path) as conn:
            rows = conn.execute("SELECT user_json FROM users").fetchall()
            return [User.model_validate_json(row[0]) for row in rows]

    @override
    @db_span("db.get_user", table="admin-db")
    def get_user(self, user_name: str, current_conn: sqlite3.Connection | None = None) -> User:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_user"})
        with _sqlite_connection(self._db_path) if current_conn is None else nullcontext(current_conn) as conn:
            row = conn.execute("SELECT user_json FROM users WHERE user_name = ?", (user_name,)).fetchone()

            if row is None:
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "user_key_error"})
                raise KeyError(f"No user with name {user_name}.")

            return User.model_validate_json(row[0])

    @override
    @db_span("db.replace_user", table="admin-db")
    def replace_user(self, user: User, current_conn: sqlite3.Connection | None = None) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "replace_user"})
        with _sqlite_connection(self._db_path) if current_conn is None else nullcontext(current_conn) as conn:
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
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "user_key_error"})
                raise KeyError(f"No user with name {user.id.name}")

    @override
    @db_span("db.add_dataset_to_user", table="admin-db")
    def add_dataset_to_user(self, username: str, dataset_name: str, initial_budget: Budget) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "add_dataset_to_user"})
        user = self.get_user(username)
        ds = DatasetOfUser(dataset_name=dataset_name, initial_budget=initial_budget)
        user.datasets = user.datasets | {dataset_name: ds}
        self.replace_user(user)

    @override
    @db_span("db.del_dataset_to_user", table="admin-db")
    def del_dataset_to_user(self, username: str, dataset_name: str) -> None:
        ADMINDB_DELETE_COUNTER.add(1, {"operation": "del_dataset_to_user"})
        user = self.get_user(username)
        del user.datasets[dataset_name]
        self.replace_user(user)

    @override
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

        user_list = UserCollection(**yaml_dict).users
        ADMINDB_INSERT_COUNTER.add(len(user_list), {"operation": "add_users_via_yaml"})

        self.load_users_collection(user_list, overwrite=overwrite)

    @override
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

        with _sqlite_connection(self._db_path) as conn:
            try:
                conn.execute(
                    """
                    INSERT into users (user_name, email, may_query, admin, user_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user.id.name, user.id.email, user.may_query, user.admin, user.model_dump_json()),
                )
            except sqlite3.IntegrityError as e:
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "user_key_error"})
                raise KeyError(f"User with name {user.id.name} already exists.") from e

    @override
    @db_span("db.del_user", table="admin-db")
    def del_user(self, user_name: str) -> None:
        ADMINDB_DELETE_COUNTER.add(1, {"operation": "del_user"})
        with _sqlite_connection(self._db_path) as conn:
            conn.execute("DELETE FROM users WHERE user_name = ?", (user_name,))

    @override
    @db_span("db.does_user_exist", table="admin-db")
    def does_user_exist(self, user_name: str) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "does_user_exist"})
        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM users WHERE user_name = ?", (user_name,)).fetchone()

            return row is not None

    @override
    @db_span("db.is_user_admin", table="admin-db")
    def is_user_admin(self, user_name: str) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "is_user_admin"})
        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT admin FROM users WHERE user_name = ?", (user_name,)).fetchone()

            if row is None:
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "user_key_error"})
                raise KeyError(f"No user with name {user_name}")

            return bool(row[0])

    @override
    @db_span("db.has_user_access_to_dataset", table="admin-db")
    def has_user_access_to_dataset(self, user_name: str, dataset_name: str) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "has_user_access_to_dataset"})
        user = self.get_user(user_name)
        return dataset_name in user.datasets

    @override
    @db_span("db.get_budget", table="admin-db")
    def get_budget(self, user_name: str, dataset_name: str, parameter: BudgetDBKey) -> Budget:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_budget"})
        user = self.get_user(user_name)
        return getattr(user.datasets[dataset_name], parameter)

    @override
    @db_span("db.set_budget", table="admin-db")
    def set_budget(
        self,
        user_name: str,
        dataset_name: str,
        parameter: BudgetDBKey,
        value: Budget,
    ) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "set_budget"})
        with self.get_db_conn() as conn:
            try:
                user = self.get_user(user_name, conn)
                setattr(user.datasets[dataset_name], parameter, value)
                self.replace_user(user, conn)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                conn.rollback()
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "any_error"})
                raise exc

    # Datasets
    ###########################################################################

    def load_dataset_collection(self, datasets: list[DSInfo], path_prefix: Path) -> None:
        """Load a list of datasets.

        Args:
            datasets (list[DSInfo]): A list of dataset info.
            path_prefix (Path): The path prefix to preprend to all paths specified in the dataset infos.
        """
        with _sqlite_connection(self._db_path) as conn:
            for ds in datasets:
                # Step 1: overwrite path
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

                # Step 2: add metadata collections (one metadata per dataset)
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

                metadata = TableMetadata.from_dict(metadata_dict)
                # Step 3: add to database
                try:
                    conn.execute(
                        """
                        INSERT INTO datasets
                        (dataset_name, dataset_json, metadata_json)
                        VALUES (?, ?, ?)
                        """,
                        (dataset_name, ds.model_dump_json(), metadata.model_dump_json()),
                    )
                except sqlite3.IntegrityError as e:
                    # Because we are in the same context, all previous inserts will be rolled back
                    ADMINDB_ERROR_COUNTER.add(1, {"operation": "dataset_key_error"})
                    raise KeyError(f"Dataset with name {dataset_name} already exists.") from e

    @override
    @db_span("db.datasets", table="admin-db")
    def datasets(self) -> list[DSInfo]:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "datasets"})
        with _sqlite_connection(self._db_path) as conn:
            rows = conn.execute("SELECT dataset_json FROM datasets").fetchall()
            return [DSInfo.model_validate_json(row[0]) for row in rows]

    @override
    @db_span("db.add_datasets_via_yaml", table="admin-db")
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
            self.drop_collection(TK.DATASETS)

        match yaml_file:
            case Path():
                yaml_dict = yaml.safe_load(yaml_file.resolve().open(encoding="utf-8"))
            case BinaryIO() | SpooledTemporaryFile():
                yaml_dict = yaml.safe_load(yaml_file)

        datasets = DatasetsCollection(**yaml_dict).datasets
        ADMINDB_INSERT_COUNTER.add(len(datasets), {"operation": "add_datasets_via_yaml"})
        self.load_dataset_collection(datasets, path_prefix)

    @override
    @db_span("db.add_dataset", table="admin-db")
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
        ds_metadata = TableMetadata.from_dict(metadata_dict)

        # Step 4: Insert into db
        with _sqlite_connection(self._db_path) as conn:
            conn.execute(
                "INSERT INTO datasets (dataset_name, dataset_json, metadata_json) VALUES (?, ?, ?)",
                (ds_info.dataset_name, ds_info.model_dump_json(), ds_metadata.model_dump_json()),
            )

    @override
    @db_span("db.delete_dataset", table="admin-db")
    def del_dataset(self, dataset_name: str) -> None:
        ADMINDB_DELETE_COUNTER.add(1, {"operation": "delete_dataset"})
        with _sqlite_connection(self._db_path) as conn:
            conn.execute("DELETE FROM datasets WHERE dataset_name = ?", (dataset_name,))

    @override
    @db_span("db.does_dataset_exist", table="admin-db")
    def does_dataset_exist(self, dataset_name: str) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "does_dataset_exist"})
        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT 1 FROM datasets WHERE dataset_name = ?", (dataset_name,)).fetchone()

            return row is not None

    @override
    @db_span("db.get_dataset", table="admin-db")
    def get_dataset(self, dataset_name: str) -> DSInfo:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_dataset"})

        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT dataset_json FROM datasets WHERE dataset_name = ?", (dataset_name,)
            ).fetchone()

            if row is None:
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "dataset_key_error"})
                raise KeyError(f"No dataset with name {dataset_name}.")

        return DSInfo.model_validate_json(row[0])

    @override
    @db_span("db.get_dataset_metadata", table="admin-db")
    def get_dataset_metadata(self, dataset_name: str) -> TableMetadata:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_dataset_metadata"})
        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute(
                "SELECT metadata_json FROM datasets WHERE dataset_name = ?", (dataset_name,)
            ).fetchone()

            if row is None:
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "dataset_key_error"})
                raise KeyError(f"No dataset with name {dataset_name}.")

            return TableMetadata.model_validate_json(row[0])

    @override
    @db_span("db.set_dataset_metadata", table="admin-db")
    def set_dataset_metadata(self, dataset_name: str, json_file: UploadFile) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "set_dataset_metadata"})
        json_file.seek(0)
        content = json_file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        metadata_dict = json.loads(content)
        validated_metadata = TableMetadata.from_dict(metadata_dict).model_dump_json()

        with _sqlite_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE datasets
                SET
                    metadata_json = ?
                WHERE dataset_name = ?
                """,
                (validated_metadata, dataset_name),
            )
            if cursor.rowcount == 0:
                ADMINDB_ERROR_COUNTER.add(1, {"operation": "dataset_key_error"})
                raise KeyError(f"No dataset with name {dataset_name}")

    # Other
    ###########################################################################

    @override
    @db_span("db.drop_collection", table="admin-db")
    def drop_collection(self, collection: TK) -> None:
        ADMINDB_DELETE_COUNTER.add(1, {"operation": "drop_collection"})

        match collection:
            case TK.USERS:
                with _sqlite_connection(self._db_path) as conn:
                    conn.execute("DELETE FROM users")
            case TK.JOBS:
                with _sqlite_connection(self._db_path) as conn:
                    conn.execute("DELETE FROM jobs")
            case TK.ARCHIVE:
                with _sqlite_connection(self._archives_db_path) as conn:
                    conn.execute("DELETE FROM archives")
            case TK.MISC_KEYS:
                with _sqlite_connection(self._db_path) as conn:
                    conn.execute("DELETE FROM misc")
            case TK.DATASETS:
                with _sqlite_connection(self._db_path) as conn:
                    conn.execute("DELETE FROM datasets")

        self._init_sqlite_dbs()

    @override
    @db_span("db.set_bootstrap", table="admin-db")
    def set_bootstrap(self, bootstrap: str) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "set_bootstrap"})
        with _sqlite_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE misc SET value = ?, disabled = ? WHERE name = ?",
                (bootstrap, int(False), MiscDBKeys.BOOTSTRAP),
            )

    @override
    @db_span("db.get_bootstrap", table="admin-db")
    def get_bootstrap(self) -> str | None:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_bootstrap"})
        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT value FROM misc WHERE name = ?", (MiscDBKeys.BOOTSTRAP,)).fetchone()
            match row:
                case (bootstrap_key, *_):
                    return bootstrap_key
                case None:
                    return None
                case _:
                    ADMINDB_ERROR_COUNTER.add(1, {"operation": "invalid_misc_value_return"})
                    raise InternalServerException("Invalid Query Returns")

    @override
    @db_span("db.set_bootstrap_disabled", table="admin-db")
    def set_bootstrap_disabled(self, bootstrap_disabled: bool = True) -> None:
        ADMINDB_INSERT_COUNTER.add(1, {"operation": "set_bootstrap_disabled"})
        with _sqlite_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE misc SET disabled = ? WHERE name = ?",
                (int(bootstrap_disabled), MiscDBKeys.BOOTSTRAP),
            )

    @override
    @db_span("db.get_bootstrap_disabled", table="admin-db")
    def get_bootstrap_disabled(self) -> bool:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "get_bootstrap_disabled"})
        with _sqlite_connection(self._db_path) as conn:
            row = conn.execute("SELECT disabled FROM misc WHERE name = ?", (MiscDBKeys.BOOTSTRAP,)).fetchone()
            match row:
                case (disabled_int, *_):
                    return bool(disabled_int)
                case None:
                    return False
                case _:
                    ADMINDB_ERROR_COUNTER.add(1, {"operation": "invalid_misc_value_return"})
                    raise InternalServerException("Invalid Query Returns")

    # Backup
    ###########################################################################

    def _sqlite_paths_to_backup(self) -> list[Path]:
        """Paths of the sqlite files that make up the database state to snapshot."""
        return [self._db_path, self._archives_db_path]

    @staticmethod
    def _snapshot_sqlite_file(src_path: Path, dest_path: Path) -> None:
        """Writes a point-in-time copy of a live sqlite db to dest_path.

        Args:
            src_path (Path): Path of the sqlite database to copy.
            dest_path (Path): Path to write the snapshot to.
        """
        with (
            closing(sqlite3.connect(src_path)) as src_conn,
            closing(sqlite3.connect(dest_path)) as dest_conn,
        ):
            src_conn.backup(dest_conn)

    @override
    @db_span("db.backup", table="admin-db")
    def backup(self) -> bytes:
        ADMINDB_QUERY_COUNTER.add(1, {"operation": "backup"})

        with TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            buffer = io.BytesIO()

            with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                for src_path in self._sqlite_paths_to_backup():
                    if not src_path.exists():
                        # If nothing writtenm, we don't save
                        continue

                    snapshot_path = tmp_path / src_path.name
                    self._snapshot_sqlite_file(src_path, snapshot_path)
                    archive.write(snapshot_path, arcname=src_path.name)

            return buffer.getvalue()

    def backup_filename(self) -> str:
        """Generates a timestamped filename.

        Returns:
            str: filename for the backup.
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        return f"lomas-admin-backup-{timestamp}.zip"

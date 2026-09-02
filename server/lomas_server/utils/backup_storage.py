from dataclasses import dataclass
from pathlib import Path

import boto3

from lomas_core.models.constants import get_lomas_logger
from lomas_server.models.config import BackupConfig, BackupS3Config

logger = get_lomas_logger(__name__)


@dataclass(frozen=True)
class BackupDestination:
    """Where a backup ended up being written."""

    location: str
    """Local path, or an s3://bucket/key URI."""
    is_s3: bool


def store_backup(
    data: bytes, filename: str, database_directory: Path, config: BackupConfig
) -> BackupDestination:
    """Persists a backup archive either to S3 or to a local directory.

    If `config.s3` is set, the archive is uploaded to that S3 bucket. Otherwise,
    it is written to `config.local_directory`, falling back to a 'backups'
    subdirectory of the server's `database_directory` if that is not set either.

    Args:
        data (bytes): The backup archive content (e.g. a zip file's bytes).
        filename (str): The filename to give the backup (e.g. 'lomas-admin-backup-....zip').
        database_directory (Path): The server's admin database directory, used
            as a fallback base directory for local backups.
        config (BackupConfig): Backup destination configuration.

    Returns:
        BackupDestination: Where the backup was written.
    """
    if config.type == "s3":
        return _store_backup_s3(data, filename, config)

    return _store_backup_local(data, filename, config.local_directory or (database_directory / "backups"))


def _store_backup_local(data: bytes, filename: str, directory: Path) -> BackupDestination:
    directory.mkdir(parents=True, exist_ok=True)
    dest_path = directory / filename
    dest_path.write_bytes(data)
    logger.info(f"Wrote admin database backup to {dest_path}.")
    return BackupDestination(location=str(dest_path), is_s3=False)


def _store_backup_s3(data: bytes, filename: str, s3_config: BackupS3Config) -> BackupDestination:
    key = f"{s3_config.key_prefix.rstrip('/')}/{filename}" if s3_config.key_prefix else filename

    client = boto3.client(
        "s3",
        endpoint_url=str(s3_config.endpoint_url) if s3_config.endpoint_url else None,
        aws_access_key_id=s3_config.access_key_id,
        aws_secret_access_key=s3_config.secret_access_key,
    )
    client.put_object(Bucket=s3_config.bucket, Key=key, Body=data)

    location = f"s3://{s3_config.bucket}/{key}"
    logger.info(f"Uploaded admin database backup to {location}.")
    return BackupDestination(location=location, is_s3=True)

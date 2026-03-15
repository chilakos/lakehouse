"""Raw zone file management for mainframe and other batch ingestion sources.

Provides the ``RawZoneManager`` class, which uploads files from a local
staging directory (SFTP / Connect:Direct drop zone) to a canonical raw zone
path on S3 or MinIO.  The original binary files are stored untouched so that
the full 7-year regulatory retention requirement can be satisfied independently
of the Bronze Iceberg tables.

Raw zone bucket structure::

    s3://{bucket}/raw/mainframe/{source_system}/{YYYY-MM-DD}/{filename}

Supports both AWS S3 (default) and MinIO (via ``endpoint_url`` override in
``RawZoneConfig``).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import boto3 as boto3_type  # noqa: F401 – type-check only

logger = logging.getLogger(__name__)


@dataclass
class RawZoneConfig:
    """Configuration for the raw zone S3/MinIO bucket.

    Args:
        bucket: Bucket name for raw zone storage.
        prefix: Top-level prefix inside the bucket (default ``"raw"``).
        region: AWS region (ignored for MinIO).
        endpoint_url: Override endpoint for MinIO or other S3-compatible
            stores.  ``None`` targets AWS S3.
    """

    bucket: str = "lakehouse-raw"
    prefix: str = "raw"
    region: str = "us-east-1"
    endpoint_url: str | None = None


@dataclass
class RawZoneFile:
    """Metadata describing a file that has been landed in the raw zone.

    Args:
        raw_path: Full S3 URI of the uploaded file, e.g.
            ``s3://lakehouse-raw/raw/mainframe/db2/2026-03-15/accounts.dat``.
        file_size_bytes: Size of the file in bytes.
        md5_checksum: Hex-encoded MD5 digest of the file contents.
        arrival_ts: ISO 8601 timestamp of when the file was uploaded.
        source_system: Identifier for the originating source system.
        business_date: Partition date in ``YYYY-MM-DD`` format.
    """

    raw_path: str
    file_size_bytes: int
    md5_checksum: str
    arrival_ts: str
    source_system: str
    business_date: str


@dataclass
class RawZoneManager:
    """Manages raw zone file operations on S3 or MinIO.

    Handles upload, checksum verification, and file discovery for the raw
    zone.  All original files are stored binary-exact — no transformation is
    applied — to satisfy regulatory retention requirements.

    Args:
        config: ``RawZoneConfig`` describing the target bucket and endpoint.
    """

    config: RawZoneConfig = field(default_factory=RawZoneConfig)

    # ---------------------------------------------------------------------------
    # Class-level helpers
    # ---------------------------------------------------------------------------

    @classmethod
    def get_raw_zone_path(cls, source_system: str, business_date: str, filename: str) -> str:
        """Construct the canonical S3 key for a raw zone file.

        Args:
            source_system: Source system identifier (e.g. ``"mainframe_db2"``).
            business_date: Partition date in ``YYYY-MM-DD`` format.
            filename: Base filename (e.g. ``"accounts.dat"``).

        Returns:
            S3 key following the pattern
            ``raw/mainframe/{source_system}/{business_date}/{filename}``.
        """
        return f"raw/mainframe/{source_system}/{business_date}/{filename}"

    # ---------------------------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------------------------

    def _get_s3_client(self):
        """Create a boto3 S3 client respecting the endpoint_url override.

        Returns:
            A ``boto3.client("s3")`` instance.
        """
        import boto3

        kwargs: dict = {"region_name": self.config.region}
        if self.config.endpoint_url:
            kwargs["endpoint_url"] = self.config.endpoint_url
        return boto3.client("s3", **kwargs)

    @staticmethod
    def _compute_md5(local_path: str) -> str:
        """Compute the MD5 checksum of a local file.

        Args:
            local_path: Absolute path to the file on disk.

        Returns:
            Hex-encoded MD5 digest string.
        """
        md5 = hashlib.md5()  # noqa: S324 – MD5 used only for integrity, not security
        with open(local_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                md5.update(chunk)
        return md5.hexdigest()

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    def upload_to_raw_zone(
        self,
        local_path: str,
        source_system: str,
        business_date: str,
    ) -> RawZoneFile:
        """Upload a file from the local staging directory to the raw zone.

        Computes an MD5 checksum before upload and records file metadata.
        The file is stored at the canonical raw zone path derived from
        ``source_system`` and ``business_date``.

        Args:
            local_path: Absolute path to the source file on disk.
            source_system: Source system identifier (e.g. ``"mainframe_db2"``).
            business_date: Partition date in ``YYYY-MM-DD`` format.

        Returns:
            ``RawZoneFile`` dataclass populated with upload metadata.

        Raises:
            FileNotFoundError: If ``local_path`` does not exist.
            botocore.exceptions.ClientError: On S3/MinIO upload failure.
        """
        import os

        if not os.path.isfile(local_path):
            raise FileNotFoundError(f"Local file not found: {local_path}")

        filename = os.path.basename(local_path)
        file_size = os.path.getsize(local_path)
        checksum = self._compute_md5(local_path)

        s3_key = self.get_raw_zone_path(source_system, business_date, filename)
        raw_path = f"s3://{self.config.bucket}/{s3_key}"

        logger.info("Uploading %s -> %s (md5=%s)", local_path, raw_path, checksum)

        s3 = self._get_s3_client()
        s3.upload_file(
            Filename=local_path,
            Bucket=self.config.bucket,
            Key=s3_key,
            ExtraArgs={"Metadata": {"md5checksum": checksum}},
        )

        arrival_ts = datetime.now(tz=UTC).isoformat()
        logger.info("Upload complete: %s (%d bytes)", raw_path, file_size)

        return RawZoneFile(
            raw_path=raw_path,
            file_size_bytes=file_size,
            md5_checksum=checksum,
            arrival_ts=arrival_ts,
            source_system=source_system,
            business_date=business_date,
        )

    def list_raw_files(self, source_system: str, business_date: str) -> list[RawZoneFile]:
        """Discover files already present in the raw zone for a given date.

        Lists all objects under the canonical prefix for the given
        ``source_system`` and ``business_date``.

        Args:
            source_system: Source system identifier.
            business_date: Partition date in ``YYYY-MM-DD`` format.

        Returns:
            List of ``RawZoneFile`` instances for each object found.
            Returns an empty list when the prefix contains no objects.
        """
        prefix = f"raw/mainframe/{source_system}/{business_date}/"
        s3 = self._get_s3_client()

        results: list[RawZoneFile] = []
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.config.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key: str = obj["Key"]
                filename = key.split("/")[-1]
                checksum = obj.get("ETag", "").strip('"')
                arrival_ts = obj.get("LastModified")
                arrival_iso = arrival_ts.isoformat() if arrival_ts else ""
                results.append(
                    RawZoneFile(
                        raw_path=f"s3://{self.config.bucket}/{key}",
                        file_size_bytes=obj.get("Size", 0),
                        md5_checksum=checksum,
                        arrival_ts=arrival_iso,
                        source_system=source_system,
                        business_date=business_date,
                    )
                )
                logger.debug("Found raw file: %s (%s)", filename, arrival_iso)

        return results

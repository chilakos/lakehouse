"""Ingestion manifest for tracking mainframe and batch files through their lifecycle.

Every file that enters the raw zone is registered in a JSON Lines manifest
stored alongside the raw data on S3/MinIO::

    s3://{bucket}/raw/_manifest/{source_system}/{YYYY-MM-DD}.jsonl

Each line is a self-contained JSON object representing one ``ManifestEntry``.
The manifest is append-friendly: status updates are appended as new records;
callers should use the *last* entry for a given ``file_id`` as the canonical
state (or use ``load_manifest`` which resolves this automatically).

Lifecycle::

    LANDED  -->  PROCESSING  -->  PROCESSED
                             \\-->  FAILED
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

# Validation patterns for path components
_SOURCE_SYSTEM_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")
_BUSINESS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_no_such_key(exc: Exception) -> bool:
    """Return True when *exc* represents an S3 ``NoSuchKey`` error.

    Checks the botocore ``ClientError`` response code when available and falls
    back to a string match for mock environments and S3-compatible stores that
    may surface the code differently.

    Args:
        exc: Exception raised by a boto3 ``get_object`` call.

    Returns:
        ``True`` if the exception indicates the key does not exist.
    """
    # Botocore ClientError carries the error code in the response dict
    response = getattr(exc, "response", None)
    if response is not None:
        code = response.get("Error", {}).get("Code", "")
        if code == "NoSuchKey":
            return True
    # Fallback: string match for mocks and S3-compatible stores
    return "NoSuchKey" in str(exc) or "NoSuchKey" in type(exc).__name__


# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_LANDED = "LANDED"
STATUS_PROCESSING = "PROCESSING"
STATUS_PROCESSED = "PROCESSED"
STATUS_FAILED = "FAILED"


@dataclass
class ManifestEntry:
    """Single entry in the ingestion manifest.

    Args:
        file_id: UUID string uniquely identifying the file across runs.
        raw_path: Full S3 URI of the raw zone file.
        source_system: Originating source system (e.g. ``"mainframe_db2"``).
        business_date: Partition date in ``YYYY-MM-DD`` format.
        file_size_bytes: File size at landing time.
        md5_checksum: Hex-encoded MD5 digest of the file.
        arrival_ts: ISO 8601 timestamp of when the file landed.
        status: Current lifecycle status: ``LANDED | PROCESSING | PROCESSED | FAILED``.
        batch_id: Optional ETL batch identifier set when processing begins.
        bronze_table: Fully-qualified Iceberg table written to, if processed.
        row_count: Number of rows written to Bronze, if processed.
        processed_ts: ISO 8601 timestamp of when processing completed.
        error_message: Error description if status is ``FAILED``.
    """

    file_id: str
    raw_path: str
    source_system: str
    business_date: str
    file_size_bytes: int
    md5_checksum: str
    arrival_ts: str
    status: str
    batch_id: str | None = None
    bronze_table: str | None = None
    row_count: int | None = None
    processed_ts: str | None = None
    error_message: str | None = None

    # ------------------------------------------------------------------
    # Serialisation helpers
    # ------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialise the entry to a single-line JSON string.

        Returns:
            JSON string with no trailing newline.
        """
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, line: str) -> ManifestEntry:
        """Deserialise a ``ManifestEntry`` from a JSON string.

        Args:
            line: A JSON string produced by ``to_json()``.

        Returns:
            ``ManifestEntry`` instance.
        """
        data = json.loads(line)
        return cls(**data)


@dataclass
class IngestionManifest:
    """Manages the ingestion manifest stored as JSON Lines on S3/MinIO.

    Args:
        bucket: S3/MinIO bucket that holds both raw files and the manifest.
        endpoint_url: Optional endpoint override for MinIO / S3-compatible
            stores.  ``None`` targets AWS S3.
        region: AWS region name (ignored for MinIO).
    """

    bucket: str = "lakehouse-raw"
    endpoint_url: str | None = None
    region: str = "us-east-1"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_s3_client(self):
        """Create a boto3 S3 client respecting the endpoint_url override.

        Returns:
            A ``boto3.client("s3")`` instance.
        """
        import boto3

        kwargs: dict = {"region_name": self.region}
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        return boto3.client("s3", **kwargs)

    @staticmethod
    def _manifest_key(source_system: str, business_date: str) -> str:
        """Compute the S3 key for a manifest file.

        Args:
            source_system: Source system identifier.
            business_date: Partition date in ``YYYY-MM-DD`` format.

        Returns:
            S3 key string, e.g. ``raw/_manifest/mainframe_db2/2026-03-15.jsonl``.

        Raises:
            ValueError: If ``source_system`` or ``business_date`` contain
                invalid characters (path traversal prevention).
        """
        if not _SOURCE_SYSTEM_RE.match(source_system):
            msg = f"Invalid source_system (alphanumeric, hyphens, underscores only): {source_system!r}"
            raise ValueError(msg)
        if not _BUSINESS_DATE_RE.match(business_date):
            msg = f"Invalid business_date (expected YYYY-MM-DD): {business_date!r}"
            raise ValueError(msg)
        return f"raw/_manifest/{source_system}/{business_date}.jsonl"

    def _append_entry(self, entry: ManifestEntry) -> None:
        """Append a single ``ManifestEntry`` to the manifest on S3.

        Reads the current manifest (if any), appends the new record, and
        writes the updated content back.

        .. warning::
            This operation is **not atomic**.  Concurrent callers writing to
            the same manifest file will race.  This is acceptable for batch
            ETL where a single Airflow task processes one source/date at a
            time.  If concurrent writes are needed in the future, switch to
            S3 conditional writes or a DynamoDB-backed manifest.

        Args:
            entry: The entry to append.
        """
        s3 = self._get_s3_client()
        key = self._manifest_key(entry.source_system, entry.business_date)

        existing = ""
        try:
            response = s3.get_object(Bucket=self.bucket, Key=key)
            existing = response["Body"].read().decode("utf-8")
        except ClientError as exc:
            if not _is_no_such_key(exc):
                raise

        updated = existing.rstrip("\n") + ("\n" if existing else "") + entry.to_json() + "\n"
        s3.put_object(Bucket=self.bucket, Key=key, Body=updated.encode("utf-8"))
        logger.debug("Appended manifest entry file_id=%s status=%s", entry.file_id, entry.status)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_file(
        self,
        raw_path: str,
        source_system: str,
        business_date: str,
        file_size_bytes: int,
        md5_checksum: str,
        arrival_ts: str,
    ) -> ManifestEntry:
        """Register a newly-landed file and create a ``LANDED`` manifest entry.

        Args:
            raw_path: Full S3 URI of the raw zone file.
            source_system: Source system identifier.
            business_date: Partition date in ``YYYY-MM-DD`` format.
            file_size_bytes: Size of the file in bytes.
            md5_checksum: Hex-encoded MD5 digest of the file.
            arrival_ts: ISO 8601 timestamp of when the file arrived.

        Returns:
            ``ManifestEntry`` with ``status=LANDED`` and a freshly generated
            ``file_id``.
        """
        entry = ManifestEntry(
            file_id=str(uuid.uuid4()),
            raw_path=raw_path,
            source_system=source_system,
            business_date=business_date,
            file_size_bytes=file_size_bytes,
            md5_checksum=md5_checksum,
            arrival_ts=arrival_ts,
            status=STATUS_LANDED,
        )
        self._append_entry(entry)
        logger.info("Registered file file_id=%s path=%s", entry.file_id, raw_path)
        return entry

    def mark_processing(self, file_id: str, batch_id: str, source_system: str, business_date: str) -> ManifestEntry:
        """Update a manifest entry to ``PROCESSING`` status.

        Args:
            file_id: UUID of the file to update.
            batch_id: ETL batch identifier for this processing run.
            source_system: Source system (needed to locate the manifest file).
            business_date: Partition date (needed to locate the manifest file).

        Returns:
            Updated ``ManifestEntry`` with ``status=PROCESSING``.

        Raises:
            KeyError: If ``file_id`` is not found in the manifest.
        """
        entries = self.load_manifest(source_system, business_date)
        entry = entries.get(file_id)
        if entry is None:
            raise KeyError(f"file_id not found in manifest: {file_id}")

        entry.status = STATUS_PROCESSING
        entry.batch_id = batch_id
        self._append_entry(entry)
        return entry

    def mark_processed(
        self,
        file_id: str,
        bronze_table: str,
        row_count: int,
        source_system: str,
        business_date: str,
    ) -> ManifestEntry:
        """Update a manifest entry to ``PROCESSED`` status.

        Args:
            file_id: UUID of the file to update.
            bronze_table: Fully-qualified Iceberg table that was written.
            row_count: Number of rows written to Bronze.
            source_system: Source system (needed to locate the manifest file).
            business_date: Partition date (needed to locate the manifest file).

        Returns:
            Updated ``ManifestEntry`` with ``status=PROCESSED``.

        Raises:
            KeyError: If ``file_id`` is not found in the manifest.
        """
        entries = self.load_manifest(source_system, business_date)
        entry = entries.get(file_id)
        if entry is None:
            raise KeyError(f"file_id not found in manifest: {file_id}")

        entry.status = STATUS_PROCESSED
        entry.bronze_table = bronze_table
        entry.row_count = row_count
        entry.processed_ts = datetime.now(tz=UTC).isoformat()
        self._append_entry(entry)
        return entry

    def mark_failed(
        self,
        file_id: str,
        error_message: str,
        source_system: str,
        business_date: str,
    ) -> ManifestEntry:
        """Update a manifest entry to ``FAILED`` status.

        Args:
            file_id: UUID of the file to update.
            error_message: Human-readable error description.
            source_system: Source system (needed to locate the manifest file).
            business_date: Partition date (needed to locate the manifest file).

        Returns:
            Updated ``ManifestEntry`` with ``status=FAILED``.

        Raises:
            KeyError: If ``file_id`` is not found in the manifest.
        """
        entries = self.load_manifest(source_system, business_date)
        entry = entries.get(file_id)
        if entry is None:
            raise KeyError(f"file_id not found in manifest: {file_id}")

        entry.status = STATUS_FAILED
        entry.error_message = error_message
        entry.processed_ts = datetime.now(tz=UTC).isoformat()
        self._append_entry(entry)
        return entry

    def load_manifest(self, source_system: str, business_date: str) -> dict[str, ManifestEntry]:
        """Read all manifest entries for a given source system and date.

        Because status updates are appended as new records, later entries for
        the same ``file_id`` supersede earlier ones.  The returned dict always
        contains the most-recent entry per ``file_id``.

        Args:
            source_system: Source system identifier.
            business_date: Partition date in ``YYYY-MM-DD`` format.

        Returns:
            Dict mapping ``file_id`` -> ``ManifestEntry`` (latest state only).
            Returns an empty dict if no manifest exists for this date.
        """
        s3 = self._get_s3_client()
        key = self._manifest_key(source_system, business_date)

        try:
            response = s3.get_object(Bucket=self.bucket, Key=key)
            content = response["Body"].read().decode("utf-8")
        except ClientError as exc:
            if _is_no_such_key(exc):
                return {}
            raise

        entries: dict[str, ManifestEntry] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            entry = ManifestEntry.from_json(line)
            entries[entry.file_id] = entry  # later entry wins

        return entries

    def get_unprocessed(self, source_system: str, business_date: str) -> list[ManifestEntry]:
        """Return all files with ``LANDED`` status for the given date.

        Args:
            source_system: Source system identifier.
            business_date: Partition date in ``YYYY-MM-DD`` format.

        Returns:
            List of ``ManifestEntry`` objects whose current status is
            ``LANDED``.  Returns an empty list if none are found.
        """
        entries = self.load_manifest(source_system, business_date)
        return [e for e in entries.values() if e.status == STATUS_LANDED]

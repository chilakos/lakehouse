"""Ingestion package for raw zone file management and ingestion manifest tracking.

Provides the ``RawZoneManager`` for uploading mainframe source files to S3/MinIO
and the ``IngestionManifest`` for tracking files through their full lifecycle
(LANDED → PROCESSING → PROCESSED / FAILED).

Example::

    from src.ingestion.raw_zone import RawZoneConfig, RawZoneManager
    from src.ingestion.manifest import IngestionManifest

    config = RawZoneConfig(bucket="lakehouse-raw")
    manager = RawZoneManager(config=config)
    raw_file = manager.upload_to_raw_zone(
        local_path="/sftp/drop/accounts.dat",
        source_system="mainframe_db2",
        business_date="2026-03-15",
    )

    manifest = IngestionManifest(bucket="lakehouse-raw")
    entry = manifest.register_file(
        raw_path=raw_file.raw_path,
        source_system=raw_file.source_system,
        business_date=raw_file.business_date,
        file_size_bytes=raw_file.file_size_bytes,
        md5_checksum=raw_file.md5_checksum,
        arrival_ts=raw_file.arrival_ts,
    )
"""

from __future__ import annotations

from src.ingestion.manifest import IngestionManifest, ManifestEntry
from src.ingestion.raw_zone import RawZoneConfig, RawZoneFile, RawZoneManager

__all__ = [
    "IngestionManifest",
    "ManifestEntry",
    "RawZoneConfig",
    "RawZoneFile",
    "RawZoneManager",
]

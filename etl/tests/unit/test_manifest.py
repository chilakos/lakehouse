"""Unit tests for the ingestion manifest module.

Tests ``ManifestEntry`` and ``IngestionManifest`` without requiring a real S3
or MinIO connection.  All S3 operations are mocked via ``unittest.mock``.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.manifest import (
    STATUS_FAILED,
    STATUS_LANDED,
    STATUS_PROCESSED,
    STATUS_PROCESSING,
    IngestionManifest,
    ManifestEntry,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(**overrides) -> ManifestEntry:
    """Create a minimal ManifestEntry for testing."""
    defaults = {
        "file_id": "test-file-id-123",
        "raw_path": "s3://lakehouse-raw/raw/mainframe/db2/2026-03-15/accounts.dat",
        "source_system": "mainframe_db2",
        "business_date": "2026-03-15",
        "file_size_bytes": 4096,
        "md5_checksum": "deadbeef",
        "arrival_ts": "2026-03-15T06:00:00+00:00",
        "status": STATUS_LANDED,
    }
    defaults.update(overrides)
    return ManifestEntry(**defaults)


def _manifest_with_mock_s3(existing_entries: list[ManifestEntry] | None = None):
    """Return an IngestionManifest wired to a mock S3 client.

    Args:
        existing_entries: Optional list of entries to pre-populate the mock
            manifest JSONL body with.

    Returns:
        Tuple of (``IngestionManifest``, ``mock_s3``).
    """
    manifest = IngestionManifest(bucket="test-bucket")
    mock_s3 = MagicMock()

    if existing_entries:
        body_text = "\n".join(e.to_json() for e in existing_entries) + "\n"
        body_mock = MagicMock()
        body_mock.read.return_value = body_text.encode()
        mock_s3.get_object.return_value = {"Body": body_mock}
    else:
        mock_s3.get_object.side_effect = Exception("NoSuchKey")

    return manifest, mock_s3


# ---------------------------------------------------------------------------
# ManifestEntry tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestManifestEntry:
    """Tests for ManifestEntry dataclass."""

    def test_manifest_entry_has_file_id(self):
        """ManifestEntry stores the file_id field."""
        entry = _make_entry(file_id="abc-123")
        assert entry.file_id == "abc-123"

    def test_manifest_entry_defaults_optional_fields(self):
        """Optional fields default to None."""
        entry = _make_entry()
        assert entry.batch_id is None
        assert entry.bronze_table is None
        assert entry.row_count is None
        assert entry.processed_ts is None
        assert entry.error_message is None

    def test_manifest_roundtrip_jsonl(self):
        """Entries serialize/deserialize correctly via JSON Lines."""
        entry = _make_entry(
            batch_id="batch-001",
            bronze_table="lakehouse.bronze.accounts",
            row_count=500,
            processed_ts="2026-03-15T07:00:00+00:00",
        )
        serialised = entry.to_json()
        # Must be valid JSON (single line)
        parsed = json.loads(serialised)
        assert parsed["file_id"] == entry.file_id
        assert parsed["batch_id"] == "batch-001"
        assert parsed["row_count"] == 500

        # Round-trip
        restored = ManifestEntry.from_json(serialised)
        assert restored.file_id == entry.file_id
        assert restored.bronze_table == entry.bronze_table
        assert restored.row_count == entry.row_count


# ---------------------------------------------------------------------------
# IngestionManifest tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIngestionManifest:
    """Tests for IngestionManifest lifecycle operations."""

    def test_register_file_creates_landed_entry(self):
        """register_file creates a new LANDED manifest entry with a UUID."""
        manifest, mock_s3 = _manifest_with_mock_s3()

        with patch.object(manifest, "_get_s3_client", return_value=mock_s3):
            entry = manifest.register_file(
                raw_path="s3://lakehouse-raw/raw/mainframe/db2/2026-03-15/accounts.dat",
                source_system="mainframe_db2",
                business_date="2026-03-15",
                file_size_bytes=1024,
                md5_checksum="abc123",
                arrival_ts="2026-03-15T06:00:00+00:00",
            )

        assert entry.status == STATUS_LANDED
        # UUID format: 8-4-4-4-12 hex characters
        assert len(entry.file_id) == 36
        assert entry.file_id.count("-") == 4
        mock_s3.put_object.assert_called_once()

    def test_mark_processing_updates_status(self):
        """mark_processing changes status to PROCESSING."""
        original = _make_entry(status=STATUS_LANDED)
        manifest, mock_s3 = _manifest_with_mock_s3(existing_entries=[original])

        with patch.object(manifest, "_get_s3_client", return_value=mock_s3):
            updated = manifest.mark_processing(
                file_id=original.file_id,
                batch_id="batch-001",
                source_system="mainframe_db2",
                business_date="2026-03-15",
            )

        assert updated.status == STATUS_PROCESSING
        assert updated.batch_id == "batch-001"

    def test_mark_processed_updates_status_and_counts(self):
        """mark_processed sets status=PROCESSED and populates row_count."""
        original = _make_entry(status=STATUS_PROCESSING, batch_id="batch-001")
        manifest, mock_s3 = _manifest_with_mock_s3(existing_entries=[original])

        with patch.object(manifest, "_get_s3_client", return_value=mock_s3):
            updated = manifest.mark_processed(
                file_id=original.file_id,
                bronze_table="lakehouse.bronze.accounts",
                row_count=42,
                source_system="mainframe_db2",
                business_date="2026-03-15",
            )

        assert updated.status == STATUS_PROCESSED
        assert updated.row_count == 42
        assert updated.bronze_table == "lakehouse.bronze.accounts"
        assert updated.processed_ts is not None

    def test_mark_failed_records_error(self):
        """mark_failed sets status=FAILED and stores the error message."""
        original = _make_entry(status=STATUS_PROCESSING, batch_id="batch-001")
        manifest, mock_s3 = _manifest_with_mock_s3(existing_entries=[original])

        with patch.object(manifest, "_get_s3_client", return_value=mock_s3):
            updated = manifest.mark_failed(
                file_id=original.file_id,
                error_message="Cobrix JAR not found",
                source_system="mainframe_db2",
                business_date="2026-03-15",
            )

        assert updated.status == STATUS_FAILED
        assert updated.error_message == "Cobrix JAR not found"
        assert updated.processed_ts is not None

    def test_get_unprocessed_filters_correctly(self):
        """get_unprocessed returns only LANDED entries."""
        landed = _make_entry(file_id="id-1", status=STATUS_LANDED)
        processing = _make_entry(file_id="id-2", status=STATUS_PROCESSING)
        processed = _make_entry(file_id="id-3", status=STATUS_PROCESSED)
        failed = _make_entry(file_id="id-4", status=STATUS_FAILED)

        manifest, mock_s3 = _manifest_with_mock_s3(
            existing_entries=[landed, processing, processed, failed]
        )

        with patch.object(manifest, "_get_s3_client", return_value=mock_s3):
            unprocessed = manifest.get_unprocessed("mainframe_db2", "2026-03-15")

        assert len(unprocessed) == 1
        assert unprocessed[0].file_id == "id-1"

    def test_load_manifest_returns_latest_entry_per_file(self):
        """load_manifest resolves duplicate file_ids, returning the last entry."""
        first = _make_entry(file_id="same-id", status=STATUS_LANDED)
        second = _make_entry(file_id="same-id", status=STATUS_PROCESSING)

        manifest, mock_s3 = _manifest_with_mock_s3(existing_entries=[first, second])

        with patch.object(manifest, "_get_s3_client", return_value=mock_s3):
            entries = manifest.load_manifest("mainframe_db2", "2026-03-15")

        assert len(entries) == 1
        assert entries["same-id"].status == STATUS_PROCESSING

    def test_load_manifest_returns_empty_dict_when_no_manifest(self):
        """load_manifest returns empty dict when manifest file does not exist."""
        manifest, mock_s3 = _manifest_with_mock_s3()  # NoSuchKey side effect

        with patch.object(manifest, "_get_s3_client", return_value=mock_s3):
            entries = manifest.load_manifest("mainframe_db2", "2026-03-15")

        assert entries == {}

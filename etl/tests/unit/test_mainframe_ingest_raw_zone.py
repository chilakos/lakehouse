"""Unit tests for the raw zone integration in MainframeBronzePipeline.

Tests the backward-compatible raw zone and manifest integration without
requiring a real Spark session, S3/MinIO connection, or Cobrix JAR.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.manifest import (
    IngestionManifest,
    ManifestEntry,
)
from src.ingestion.raw_zone import RawZoneConfig
from src.pipelines.bronze.mainframe_ingest import MainframeBronzePipeline

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pipeline(raw_zone_config=None, manifest=None, manifest_entry=None):
    """Create a MainframeBronzePipeline with mocked Spark."""
    mock_spark = MagicMock()
    return MainframeBronzePipeline(
        spark=mock_spark,
        copybook_path="/tmp/test.cpy",
        data_path="s3://lakehouse-raw/raw/mainframe/mainframe_db2/2026-03-15/accounts.dat",
        source_system="mainframe_db2",
        batch_id="batch-001",
        raw_zone_config=raw_zone_config,
        manifest=manifest,
        manifest_entry=manifest_entry,
    )


def _make_manifest_entry(status="LANDED"):
    return ManifestEntry(
        file_id="file-id-001",
        raw_path="s3://lakehouse-raw/raw/mainframe/mainframe_db2/2026-03-15/accounts.dat",
        source_system="mainframe_db2",
        business_date="2026-03-15",
        file_size_bytes=2048,
        md5_checksum="abc123",
        arrival_ts="2026-03-15T06:00:00+00:00",
        status=status,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMainframePipelineBackwardCompatible:
    """Pipeline must work without raw_zone_config (original behaviour)."""

    def test_backward_compatible_without_raw_zone(self):
        """Pipeline instantiates and extract() works without raw_zone_config."""
        pipeline = _make_pipeline()
        assert pipeline._raw_zone_config is None
        assert pipeline._manifest is None
        assert pipeline._manifest_entry is None

    def test_extract_skips_raw_zone_check_when_not_configured(self):
        """extract() does NOT call list_raw_files when raw_zone_config is None."""
        pipeline = _make_pipeline()

        with (
            patch("src.pipelines.bronze.mainframe_ingest.is_cobrix_available", return_value=True),
            patch.object(pipeline, "_verify_raw_zone_file") as mock_verify,
        ):
            pipeline.extract()

        mock_verify.assert_not_called()


@pytest.mark.unit
class TestMainframePipelineRawZoneVerification:
    """extract() verifies raw zone file when raw_zone_config is provided."""

    def test_extract_with_raw_zone_verifies_path(self):
        """extract() calls _verify_raw_zone_file when raw_zone_config is set."""
        config = RawZoneConfig(bucket="test-bucket")
        pipeline = _make_pipeline(raw_zone_config=config)

        with (
            patch("src.pipelines.bronze.mainframe_ingest.is_cobrix_available", return_value=True),
            patch.object(pipeline, "_verify_raw_zone_file") as mock_verify,
        ):
            pipeline.extract()

        mock_verify.assert_called_once()

    def test_verify_raw_zone_file_raises_when_not_found(self):
        """_verify_raw_zone_file raises FileNotFoundError when file absent."""
        config = RawZoneConfig(bucket="test-bucket")
        pipeline = _make_pipeline(raw_zone_config=config)

        with (
            patch("src.ingestion.raw_zone.RawZoneManager.list_raw_files", return_value=[]),
            pytest.raises(FileNotFoundError, match="accounts.dat"),
        ):
            pipeline._verify_raw_zone_file()


@pytest.mark.unit
class TestMainframePipelineManifestIntegration:
    """execute() updates manifest on success or failure."""

    def test_execute_updates_manifest_on_success(self):
        """execute() marks manifest PROCESSED after successful run."""
        config = RawZoneConfig(bucket="test-bucket")
        entry = _make_manifest_entry(status="PROCESSING")
        mock_manifest = MagicMock(spec=IngestionManifest)
        pipeline = _make_pipeline(
            raw_zone_config=config,
            manifest=mock_manifest,
            manifest_entry=entry,
        )

        # Stub out the base execute to simulate success
        with patch.object(
            pipeline.__class__.__bases__[0],
            "execute",
            return_value={"rows_written": 100, "quality": {}},
        ):
            result = pipeline.execute()

        mock_manifest.mark_processed.assert_called_once_with(
            file_id="file-id-001",
            bronze_table=pipeline.config.full_table_name,
            row_count=100,
            source_system="mainframe_db2",
            business_date="2026-03-15",
        )
        assert result["rows_written"] == 100

    def test_execute_updates_manifest_on_failure(self):
        """execute() marks manifest FAILED when an exception is raised."""
        config = RawZoneConfig(bucket="test-bucket")
        entry = _make_manifest_entry(status="PROCESSING")
        mock_manifest = MagicMock(spec=IngestionManifest)
        pipeline = _make_pipeline(
            raw_zone_config=config,
            manifest=mock_manifest,
            manifest_entry=entry,
        )

        boom = RuntimeError("Cobrix exploded")
        with (
            patch.object(
                pipeline.__class__.__bases__[0],
                "execute",
                side_effect=boom,
            ),
            pytest.raises(RuntimeError, match="Cobrix exploded"),
        ):
            pipeline.execute()

        mock_manifest.mark_failed.assert_called_once_with(
            file_id="file-id-001",
            error_message="Cobrix exploded",
            source_system="mainframe_db2",
            business_date="2026-03-15",
        )

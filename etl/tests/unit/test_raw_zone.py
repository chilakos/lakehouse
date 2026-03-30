"""Unit tests for the raw zone file management module.

Tests ``RawZoneConfig``, ``RawZoneFile``, and ``RawZoneManager`` without
requiring any real S3 or MinIO connection.  All S3 operations are mocked via
``unittest.mock``.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
from datetime import UTC
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion.raw_zone import RawZoneConfig, RawZoneFile, RawZoneManager


@pytest.mark.unit
class TestRawZoneConfig:
    """Tests for RawZoneConfig dataclass defaults and overrides."""

    def test_raw_zone_config_defaults(self):
        """Default config values are correct."""
        config = RawZoneConfig()
        assert config.bucket == "lakehouse-raw"
        assert config.prefix == "raw"
        assert config.region == "us-east-1"
        assert config.endpoint_url is None

    def test_raw_zone_config_minio_override(self):
        """endpoint_url can be set for MinIO."""
        config = RawZoneConfig(
            bucket="minio-raw",
            endpoint_url="http://localhost:9000",
            region="us-east-1",
        )
        assert config.endpoint_url == "http://localhost:9000"
        assert config.bucket == "minio-raw"


@pytest.mark.unit
class TestRawZoneFile:
    """Tests for RawZoneFile dataclass."""

    def test_raw_zone_file_dataclass(self):
        """RawZoneFile holds all required fields."""
        rzf = RawZoneFile(
            raw_path="s3://lakehouse-raw/raw/mainframe/db2/2026-03-15/accounts.dat",
            file_size_bytes=1024,
            md5_checksum="abc123",
            arrival_ts="2026-03-15T06:00:00+00:00",
            source_system="mainframe_db2",
            business_date="2026-03-15",
        )
        assert rzf.raw_path == "s3://lakehouse-raw/raw/mainframe/db2/2026-03-15/accounts.dat"
        assert rzf.file_size_bytes == 1024
        assert rzf.md5_checksum == "abc123"
        assert rzf.arrival_ts == "2026-03-15T06:00:00+00:00"
        assert rzf.source_system == "mainframe_db2"
        assert rzf.business_date == "2026-03-15"


@pytest.mark.unit
class TestRawZoneManagerPathHelpers:
    """Tests for RawZoneManager path construction."""

    def test_get_raw_zone_path_format(self):
        """Path follows raw/mainframe/{source}/{date}/{file} convention."""
        path = RawZoneManager.get_raw_zone_path("mainframe_db2", "2026-03-15", "accounts.dat")
        assert path == "raw/mainframe/mainframe_db2/2026-03-15/accounts.dat"

    def test_get_raw_zone_path_different_source(self):
        """Path is constructed correctly for a different source system."""
        path = RawZoneManager.get_raw_zone_path("vsam_cics", "2026-01-01", "positions.dat")
        assert path == "raw/mainframe/vsam_cics/2026-01-01/positions.dat"


@pytest.mark.unit
class TestRawZoneManagerUpload:
    """Tests for RawZoneManager.upload_to_raw_zone."""

    def test_upload_to_raw_zone_calls_s3(self):
        """upload_to_raw_zone calls boto3 upload_file with correct args."""
        config = RawZoneConfig(bucket="test-bucket")
        manager = RawZoneManager(config=config)

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            tmp.write(b"EBCDIC data")
            tmp_path = tmp.name

        try:
            mock_s3 = MagicMock()
            with patch.object(manager, "_get_s3_client", return_value=mock_s3):
                manager.upload_to_raw_zone(
                    local_path=tmp_path,
                    source_system="mainframe_db2",
                    business_date="2026-03-15",
                )

            mock_s3.upload_file.assert_called_once()
            call_kwargs = mock_s3.upload_file.call_args
            assert call_kwargs.kwargs["Bucket"] == "test-bucket"
            expected_key = f"raw/mainframe/mainframe_db2/2026-03-15/{os.path.basename(tmp_path)}"
            assert call_kwargs.kwargs["Key"] == expected_key
        finally:
            os.unlink(tmp_path)

    def test_upload_computes_checksum(self):
        """upload_to_raw_zone computes MD5 and returns it in RawZoneFile."""
        config = RawZoneConfig(bucket="test-bucket")
        manager = RawZoneManager(config=config)
        content = b"test mainframe binary data"
        expected_md5 = hashlib.md5(content).hexdigest()  # noqa: S324

        with tempfile.NamedTemporaryFile(suffix=".dat", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            mock_s3 = MagicMock()
            with patch.object(manager, "_get_s3_client", return_value=mock_s3):
                result = manager.upload_to_raw_zone(
                    local_path=tmp_path,
                    source_system="mainframe_db2",
                    business_date="2026-03-15",
                )

            assert result.md5_checksum == expected_md5
            assert result.file_size_bytes == len(content)
            assert result.source_system == "mainframe_db2"
            assert result.business_date == "2026-03-15"
        finally:
            os.unlink(tmp_path)

    def test_upload_raises_on_missing_file(self):
        """upload_to_raw_zone raises FileNotFoundError for nonexistent paths."""
        config = RawZoneConfig(bucket="test-bucket")
        manager = RawZoneManager(config=config)
        with pytest.raises(FileNotFoundError):
            manager.upload_to_raw_zone(
                local_path="/nonexistent/path/file.dat",
                source_system="mainframe_db2",
                business_date="2026-03-15",
            )


@pytest.mark.unit
class TestRawZoneManagerList:
    """Tests for RawZoneManager.list_raw_files."""

    def test_list_raw_files(self):
        """list_raw_files returns RawZoneFile instances for each S3 object."""
        from datetime import datetime

        config = RawZoneConfig(bucket="test-bucket")
        manager = RawZoneManager(config=config)

        fake_dt = datetime(2026, 3, 15, 6, 0, 0, tzinfo=UTC)
        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {
                        "Key": "raw/mainframe/mainframe_db2/2026-03-15/accounts.dat",
                        "Size": 2048,
                        "ETag": '"deadbeef"',
                        "LastModified": fake_dt,
                    }
                ]
            }
        ]

        with patch.object(manager, "_get_s3_client", return_value=mock_s3):
            results = manager.list_raw_files("mainframe_db2", "2026-03-15")

        assert len(results) == 1
        assert results[0].raw_path == "s3://test-bucket/raw/mainframe/mainframe_db2/2026-03-15/accounts.dat"
        assert results[0].file_size_bytes == 2048
        assert results[0].source_system == "mainframe_db2"
        assert results[0].business_date == "2026-03-15"

    def test_list_raw_files_empty(self):
        """list_raw_files returns empty list when no objects exist."""
        config = RawZoneConfig(bucket="test-bucket")
        manager = RawZoneManager(config=config)

        mock_s3 = MagicMock()
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{}]  # no Contents key

        with patch.object(manager, "_get_s3_client", return_value=mock_s3):
            results = manager.list_raw_files("mainframe_db2", "2026-03-15")

        assert results == []

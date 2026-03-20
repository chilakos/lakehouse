"""Unit tests for DataStage job inventory module.

Tests the DataStageJob model, JobComplexity enum, and JobInventory class
for CRUD, filtering, classification, statistics, and JSON persistence.

@pytest.mark.unit
"""

from __future__ import annotations

import os
import tempfile

import pytest


@pytest.mark.unit
class TestJobComplexity:
    """Tests for JobComplexity enum values."""

    def test_complexity_enum_has_simple(self):
        """JobComplexity must have SIMPLE value."""
        from src.inventory.models import JobComplexity

        assert JobComplexity.SIMPLE.value == "simple"

    def test_complexity_enum_has_medium(self):
        """JobComplexity must have MEDIUM value."""
        from src.inventory.models import JobComplexity

        assert JobComplexity.MEDIUM.value == "medium"

    def test_complexity_enum_has_complex(self):
        """JobComplexity must have COMPLEX value."""
        from src.inventory.models import JobComplexity

        assert JobComplexity.COMPLEX.value == "complex"


@pytest.mark.unit
class TestDataStageJob:
    """Tests for DataStageJob dataclass serialization."""

    def _make_job(self, **overrides):
        """Helper to create a DataStageJob with defaults."""
        from src.inventory.models import DataStageJob, JobComplexity

        defaults = {
            "job_name": "DS_TRADES_DAILY",
            "job_id": "ds-001",
            "complexity": JobComplexity.SIMPLE,
            "source_systems": ["trading_platform"],
            "target_tables": ["bronze.trades"],
            "dependencies": [],
            "estimated_effort_hours": 8.0,
            "has_mainframe_source": False,
            "transformation_description": "Simple daily trade load",
            "schedule": "0 6 * * *",
            "avg_runtime_minutes": 15.0,
            "row_volume_estimate": 50000,
            "migration_status": "not_started",
            "notes": "",
        }
        defaults.update(overrides)
        return DataStageJob(**defaults)

    def test_to_dict_roundtrip(self):
        """DataStageJob.to_dict() produces dict that from_dict() can restore."""
        from src.inventory.models import DataStageJob

        job = self._make_job()
        d = job.to_dict()
        restored = DataStageJob.from_dict(d)
        assert restored.job_name == job.job_name
        assert restored.job_id == job.job_id
        assert restored.complexity == job.complexity
        assert restored.source_systems == job.source_systems
        assert restored.estimated_effort_hours == job.estimated_effort_hours

    def test_to_dict_contains_all_fields(self):
        """to_dict() must include all DataStageJob fields."""
        job = self._make_job()
        d = job.to_dict()
        expected_keys = {
            "job_name",
            "job_id",
            "complexity",
            "source_systems",
            "target_tables",
            "dependencies",
            "estimated_effort_hours",
            "has_mainframe_source",
            "transformation_description",
            "schedule",
            "avg_runtime_minutes",
            "row_volume_estimate",
            "migration_status",
            "notes",
        }
        assert expected_keys == set(d.keys())

    def test_to_dict_complexity_is_string(self):
        """to_dict() serializes complexity as string value."""
        job = self._make_job()
        d = job.to_dict()
        assert d["complexity"] == "simple"

    def test_from_dict_restores_complexity_enum(self):
        """from_dict() restores complexity string back to JobComplexity enum."""
        from src.inventory.models import DataStageJob, JobComplexity

        d = self._make_job().to_dict()
        restored = DataStageJob.from_dict(d)
        assert isinstance(restored.complexity, JobComplexity)
        assert restored.complexity == JobComplexity.SIMPLE

    def test_from_dict_with_notes(self):
        """from_dict() handles optional notes field."""
        from src.inventory.models import DataStageJob

        job = self._make_job(notes="Migration in progress")
        d = job.to_dict()
        restored = DataStageJob.from_dict(d)
        assert restored.notes == "Migration in progress"


@pytest.mark.unit
class TestJobInventory:
    """Tests for JobInventory CRUD, filtering, and statistics."""

    def _make_inventory(self):
        """Helper to create a JobInventory with sample jobs."""
        from src.inventory.catalog import JobInventory
        from src.inventory.models import DataStageJob, JobComplexity

        jobs = [
            DataStageJob(
                job_name="DS_TRADES_DAILY",
                job_id="ds-001",
                complexity=JobComplexity.SIMPLE,
                source_systems=["trading_platform"],
                target_tables=["bronze.trades"],
                dependencies=[],
                estimated_effort_hours=8.0,
                has_mainframe_source=False,
                transformation_description="Simple daily trade load",
                schedule="0 6 * * *",
                avg_runtime_minutes=15.0,
                row_volume_estimate=50000,
                migration_status="not_started",
            ),
            DataStageJob(
                job_name="DS_POSITIONS_MULTI",
                job_id="ds-002",
                complexity=JobComplexity.MEDIUM,
                source_systems=["trading_platform", "risk_engine"],
                target_tables=["bronze.positions"],
                dependencies=["ds-001"],
                estimated_effort_hours=24.0,
                has_mainframe_source=False,
                transformation_description="Multi-source position joins",
                schedule="0 7 * * *",
                avg_runtime_minutes=45.0,
                row_volume_estimate=200000,
                migration_status="in_progress",
            ),
            DataStageJob(
                job_name="DS_MF_ACCOUNTS",
                job_id="ds-003",
                complexity=JobComplexity.COMPLEX,
                source_systems=["mainframe_db2"],
                target_tables=["bronze.accounts"],
                dependencies=[],
                estimated_effort_hours=80.0,
                has_mainframe_source=True,
                transformation_description="Mainframe COBOL account extract",
                schedule="0 2 * * *",
                avg_runtime_minutes=120.0,
                row_volume_estimate=500000,
                migration_status="not_started",
            ),
            DataStageJob(
                job_name="DS_REF_DATA",
                job_id="ds-004",
                complexity=JobComplexity.SIMPLE,
                source_systems=["reference_db"],
                target_tables=["bronze.ref_data"],
                dependencies=[],
                estimated_effort_hours=4.0,
                has_mainframe_source=False,
                transformation_description="Reference data lookup load",
                schedule="0 5 * * *",
                avg_runtime_minutes=5.0,
                row_volume_estimate=10000,
                migration_status="completed",
            ),
        ]

        inventory = JobInventory(jobs=jobs)
        return inventory

    def test_add_job(self):
        """add_job() appends a job to the inventory."""
        from src.inventory.catalog import JobInventory
        from src.inventory.models import DataStageJob, JobComplexity

        inventory = JobInventory()
        job = DataStageJob(
            job_name="NEW_JOB",
            job_id="ds-099",
            complexity=JobComplexity.SIMPLE,
            source_systems=["test"],
            target_tables=["bronze.test"],
            dependencies=[],
            estimated_effort_hours=2.0,
            has_mainframe_source=False,
            transformation_description="Test",
            schedule="0 0 * * *",
            avg_runtime_minutes=1.0,
            row_volume_estimate=100,
            migration_status="not_started",
        )
        inventory.add_job(job)
        assert len(inventory.jobs) == 1
        assert inventory.jobs[0].job_id == "ds-099"

    def test_remove_job(self):
        """remove_job() removes a job by job_id."""
        inventory = self._make_inventory()
        initial_count = len(inventory.jobs)
        inventory.remove_job("ds-002")
        assert len(inventory.jobs) == initial_count - 1
        assert all(j.job_id != "ds-002" for j in inventory.jobs)

    def test_filter_by_complexity(self):
        """filter_by_complexity() returns jobs matching the given complexity."""
        from src.inventory.models import JobComplexity

        inventory = self._make_inventory()
        simple_jobs = inventory.filter_by_complexity(JobComplexity.SIMPLE)
        assert len(simple_jobs) == 2
        assert all(j.complexity == JobComplexity.SIMPLE for j in simple_jobs)

    def test_filter_by_source_system(self):
        """filter_by_source_system() returns jobs with the given source system."""
        inventory = self._make_inventory()
        mf_jobs = inventory.filter_by_source_system("mainframe_db2")
        assert len(mf_jobs) == 1
        assert mf_jobs[0].job_id == "ds-003"

    def test_filter_by_status(self):
        """filter_by_status() returns jobs with the given migration status."""
        inventory = self._make_inventory()
        not_started = inventory.filter_by_status("not_started")
        assert len(not_started) == 2

    def test_get_migration_stats(self):
        """get_migration_stats() returns counts by complexity, status, and total hours."""
        inventory = self._make_inventory()
        stats = inventory.get_migration_stats()

        assert stats["by_complexity"]["simple"] == 2
        assert stats["by_complexity"]["medium"] == 1
        assert stats["by_complexity"]["complex"] == 1

        assert stats["by_status"]["not_started"] == 2
        assert stats["by_status"]["in_progress"] == 1
        assert stats["by_status"]["completed"] == 1

        assert stats["total_estimated_hours"] == 116.0
        assert stats["total_jobs"] == 4

    def test_save_and_load_json_roundtrip(self):
        """save_to_json() and load_from_json() produce identical inventory."""
        from src.inventory.catalog import JobInventory

        inventory = self._make_inventory()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            tmp_path = f.name

        try:
            inventory.save_to_json(tmp_path)
            loaded = JobInventory.load_from_json(tmp_path)

            assert len(loaded.jobs) == len(inventory.jobs)
            for orig, restored in zip(inventory.jobs, loaded.jobs, strict=False):
                assert orig.job_id == restored.job_id
                assert orig.job_name == restored.job_name
                assert orig.complexity == restored.complexity
        finally:
            os.unlink(tmp_path)

    def test_classify_complexity_simple(self):
        """classify_complexity() returns SIMPLE for single-source, no-mainframe job."""
        from src.inventory.catalog import JobInventory
        from src.inventory.models import DataStageJob, JobComplexity

        job = DataStageJob(
            job_name="SIMPLE_JOB",
            job_id="test-001",
            complexity=JobComplexity.SIMPLE,  # will be overridden
            source_systems=["single_source"],
            target_tables=["bronze.test"],
            dependencies=[],
            estimated_effort_hours=4.0,
            has_mainframe_source=False,
            transformation_description="Basic load",
            schedule="daily",
            avg_runtime_minutes=5.0,
            row_volume_estimate=1000,
            migration_status="not_started",
        )
        inv = JobInventory()
        result = inv.classify_complexity(job)
        assert result == JobComplexity.SIMPLE

    def test_classify_complexity_medium(self):
        """classify_complexity() returns MEDIUM for multi-source job."""
        from src.inventory.catalog import JobInventory
        from src.inventory.models import DataStageJob, JobComplexity

        job = DataStageJob(
            job_name="MEDIUM_JOB",
            job_id="test-002",
            complexity=JobComplexity.SIMPLE,
            source_systems=["source_a", "source_b"],
            target_tables=["bronze.test"],
            dependencies=["dep-001"],
            estimated_effort_hours=20.0,
            has_mainframe_source=False,
            transformation_description="Multi-source join with lookups",
            schedule="daily",
            avg_runtime_minutes=30.0,
            row_volume_estimate=50000,
            migration_status="not_started",
        )
        inv = JobInventory()
        result = inv.classify_complexity(job)
        assert result == JobComplexity.MEDIUM

    def test_classify_complexity_complex_mainframe(self):
        """classify_complexity() returns COMPLEX for mainframe-sourced job."""
        from src.inventory.catalog import JobInventory
        from src.inventory.models import DataStageJob, JobComplexity

        job = DataStageJob(
            job_name="COMPLEX_JOB",
            job_id="test-003",
            complexity=JobComplexity.SIMPLE,
            source_systems=["mainframe_db2"],
            target_tables=["bronze.accounts"],
            dependencies=[],
            estimated_effort_hours=80.0,
            has_mainframe_source=True,
            transformation_description="Mainframe COBOL extract",
            schedule="daily",
            avg_runtime_minutes=120.0,
            row_volume_estimate=500000,
            migration_status="not_started",
        )
        inv = JobInventory()
        result = inv.classify_complexity(job)
        assert result == JobComplexity.COMPLEX

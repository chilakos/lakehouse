"""Inventory management utilities for DataStage job catalog.

Provides JobInventory class with CRUD operations, filtering,
complexity classification, migration statistics, and JSON persistence.

Usage:
    from src.inventory.catalog import JobInventory
    from src.inventory.models import DataStageJob, JobComplexity

    inventory = JobInventory.load_from_json("inventory.json")
    complex_jobs = inventory.filter_by_complexity(JobComplexity.COMPLEX)
    stats = inventory.get_migration_stats()
"""

from __future__ import annotations

import json
import logging
from collections import Counter

from src.inventory.models import DataStageJob, JobComplexity

logger = logging.getLogger(__name__)


class JobInventory:
    """Manages a collection of DataStage jobs for migration planning.

    Supports CRUD operations, filtering by complexity/source/status,
    migration statistics, complexity classification, and JSON persistence.

    Args:
        jobs: Initial list of DataStageJob instances. Defaults to empty.
    """

    def __init__(self, jobs: list[DataStageJob] | None = None) -> None:
        self.jobs: list[DataStageJob] = jobs if jobs is not None else []

    def add_job(self, job: DataStageJob) -> None:
        """Add a job to the inventory.

        Args:
            job: DataStageJob to add.
        """
        self.jobs.append(job)
        logger.info("Added job: %s (%s)", job.job_name, job.job_id)

    def remove_job(self, job_id: str) -> None:
        """Remove a job from the inventory by job_id.

        Args:
            job_id: Unique identifier of the job to remove.
        """
        self.jobs = [j for j in self.jobs if j.job_id != job_id]
        logger.info("Removed job: %s", job_id)

    def filter_by_complexity(self, complexity: JobComplexity) -> list[DataStageJob]:
        """Filter jobs by complexity level.

        Args:
            complexity: JobComplexity enum value to filter by.

        Returns:
            List of jobs matching the specified complexity.
        """
        return [j for j in self.jobs if j.complexity == complexity]

    def filter_by_source_system(self, system: str) -> list[DataStageJob]:
        """Filter jobs that use a specific source system.

        Args:
            system: Source system identifier to filter by.

        Returns:
            List of jobs with the given source system in their source_systems list.
        """
        return [j for j in self.jobs if system in j.source_systems]

    def filter_by_status(self, status: str) -> list[DataStageJob]:
        """Filter jobs by migration status.

        Args:
            status: Migration status string (not_started, in_progress, completed, blocked).

        Returns:
            List of jobs with the specified migration status.
        """
        return [j for j in self.jobs if j.migration_status == status]

    def get_migration_stats(self) -> dict:
        """Compute migration statistics for the inventory.

        Returns:
            Dict with:
                total_jobs: Total number of jobs.
                by_complexity: Counts per complexity level.
                by_status: Counts per migration status.
                total_estimated_hours: Sum of estimated effort hours.
                total_row_volume: Sum of row volume estimates.
        """
        by_complexity = Counter(j.complexity.value for j in self.jobs)
        by_status = Counter(j.migration_status for j in self.jobs)
        total_hours = sum(j.estimated_effort_hours for j in self.jobs)
        total_volume = sum(j.row_volume_estimate for j in self.jobs)

        return {
            "total_jobs": len(self.jobs),
            "by_complexity": dict(by_complexity),
            "by_status": dict(by_status),
            "total_estimated_hours": total_hours,
            "total_row_volume": total_volume,
        }

    def classify_complexity(self, job: DataStageJob) -> JobComplexity:
        """Classify a job's complexity based on its characteristics.

        Rules (applied in priority order):
        - COMPLEX: has_mainframe_source is True, or description mentions COBOL/mainframe
        - MEDIUM: multiple source systems, or has dependencies
        - SIMPLE: single source, no mainframe, no dependencies

        Args:
            job: DataStageJob to classify.

        Returns:
            JobComplexity classification.
        """
        description_lower = job.transformation_description.lower()

        # COMPLEX: mainframe source, COBOL, or multi-step
        if job.has_mainframe_source:
            return JobComplexity.COMPLEX
        if any(kw in description_lower for kw in ("cobol", "mainframe", "ebcdic", "multi-step")):
            return JobComplexity.COMPLEX

        # MEDIUM: multi-source or has dependencies
        if len(job.source_systems) > 1:
            return JobComplexity.MEDIUM
        if len(job.dependencies) > 0:
            return JobComplexity.MEDIUM
        if any(kw in description_lower for kw in ("join", "lookup", "multi-source")):
            return JobComplexity.MEDIUM

        # SIMPLE: everything else
        return JobComplexity.SIMPLE

    def save_to_json(self, path: str) -> None:
        """Persist the inventory to a JSON file.

        Args:
            path: File path to write the JSON inventory.
        """
        data = [job.to_dict() for job in self.jobs]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved %d jobs to %s", len(self.jobs), path)

    @classmethod
    def load_from_json(cls, path: str) -> JobInventory:
        """Load an inventory from a JSON file.

        Args:
            path: File path to read the JSON inventory from.

        Returns:
            JobInventory populated with the loaded jobs.
        """
        with open(path) as f:
            data = json.load(f)
        jobs = [DataStageJob.from_dict(item) for item in data]
        logger.info("Loaded %d jobs from %s", len(jobs), path)
        return cls(jobs=jobs)

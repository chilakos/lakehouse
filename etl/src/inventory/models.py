"""DataStage job inventory data model with complexity classification.

Provides:
- JobComplexity enum: SIMPLE, MEDIUM, COMPLEX
- DataStageJob dataclass with all metadata fields for migration planning

Per locked decision: Full structured catalog with complexity classification,
source systems, dependencies, estimated effort per job.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class JobComplexity(Enum):
    """Complexity classification for DataStage jobs.

    Used to estimate migration effort and prioritize pilot selection.
    - SIMPLE: Single source, basic transform, no mainframe
    - MEDIUM: Multi-source joins, lookups, moderate logic
    - COMPLEX: Mainframe, COBOL, multi-step, high business logic
    """

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


@dataclass
class DataStageJob:
    """Represents a DataStage job in the migration inventory.

    Captures all metadata needed for migration planning: complexity
    classification, source systems, dependencies, estimated effort,
    and migration status tracking.

    Attributes:
        job_name: Human-readable DataStage job name.
        job_id: Unique identifier for the job.
        complexity: Complexity classification (SIMPLE, MEDIUM, COMPLEX).
        source_systems: List of source system identifiers.
        target_tables: List of target table names.
        dependencies: List of job_ids this job depends on.
        estimated_effort_hours: Estimated migration effort in hours.
        has_mainframe_source: Whether the job reads from mainframe.
        transformation_description: Human-readable description of transformations.
        schedule: Cron schedule or schedule description.
        avg_runtime_minutes: Average runtime in minutes.
        row_volume_estimate: Estimated row count per run.
        migration_status: Current status (not_started, in_progress, completed, blocked).
        notes: Optional freeform notes.
    """

    job_name: str
    job_id: str
    complexity: JobComplexity
    source_systems: list[str]
    target_tables: list[str]
    dependencies: list[str]
    estimated_effort_hours: float
    has_mainframe_source: bool
    transformation_description: str
    schedule: str
    avg_runtime_minutes: float
    row_volume_estimate: int
    migration_status: str
    notes: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON persistence.

        Converts JobComplexity enum to its string value.

        Returns:
            Dictionary with all fields, complexity as string.
        """
        return {
            "job_name": self.job_name,
            "job_id": self.job_id,
            "complexity": self.complexity.value,
            "source_systems": self.source_systems,
            "target_tables": self.target_tables,
            "dependencies": self.dependencies,
            "estimated_effort_hours": self.estimated_effort_hours,
            "has_mainframe_source": self.has_mainframe_source,
            "transformation_description": self.transformation_description,
            "schedule": self.schedule,
            "avg_runtime_minutes": self.avg_runtime_minutes,
            "row_volume_estimate": self.row_volume_estimate,
            "migration_status": self.migration_status,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> DataStageJob:
        """Deserialize from dictionary (e.g., loaded from JSON).

        Converts complexity string back to JobComplexity enum.

        Args:
            data: Dictionary with DataStageJob fields.

        Returns:
            Restored DataStageJob instance.
        """
        return cls(
            job_name=data["job_name"],
            job_id=data["job_id"],
            complexity=JobComplexity(data["complexity"]),
            source_systems=data["source_systems"],
            target_tables=data["target_tables"],
            dependencies=data["dependencies"],
            estimated_effort_hours=data["estimated_effort_hours"],
            has_mainframe_source=data["has_mainframe_source"],
            transformation_description=data["transformation_description"],
            schedule=data["schedule"],
            avg_runtime_minutes=data["avg_runtime_minutes"],
            row_volume_estimate=data["row_volume_estimate"],
            migration_status=data["migration_status"],
            notes=data.get("notes", ""),
        )

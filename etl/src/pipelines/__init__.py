"""ETL pipeline framework with medallion architecture enforcement.

Provides the core pipeline abstractions:
- BasePipeline: Abstract base class enforcing extract/transform/validate/write contract
- PipelineConfig: Frozen dataclass for pipeline configuration
- MedallionLayer: Enum for Bronze/Silver/Gold layer targeting
- SchemaValidationError: Raised when DataFrame schema doesn't match target
- QualityGateError: Raised when critical quality checks fail
"""

from src.pipelines.base import (
    BasePipeline,
    MedallionLayer,
    PipelineConfig,
    QualityGateError,
    SchemaValidationError,
)

__all__ = [
    "BasePipeline",
    "MedallionLayer",
    "PipelineConfig",
    "QualityGateError",
    "SchemaValidationError",
]

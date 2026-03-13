"""Base pipeline class with medallion architecture enforcement.

Provides the abstract base class that all ETL pipelines must extend.
Enforces the extract -> transform -> validate_schema -> quality_check -> write
contract so that schema validation and quality gates cannot be bypassed.

Uses TYPE_CHECKING pattern for PySpark imports (consistent with catalog.py).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.types import StructType

from pyspark.sql.functions import current_timestamp, lit

logger = logging.getLogger(__name__)


class MedallionLayer(Enum):
    """Medallion architecture layer designation."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class SchemaValidationError(Exception):
    """Raised when a DataFrame schema does not match the target StructType."""


class QualityGateError(Exception):
    """Raised when critical quality checks fail, blocking layer promotion."""


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration for a medallion pipeline.

    Attributes:
        name: Human-readable pipeline name.
        target_layer: Target medallion layer (BRONZE, SILVER, GOLD).
        target_table: Target table name within the layer namespace.
        target_schema: PySpark StructType defining the expected output schema.
        source_layer: Source medallion layer (None for external sources).
        quality_checks_path: Path to Soda quality checks YAML (Plan 04).
        critical_checks: List of check names that block on failure.
        max_retries: Maximum retry attempts for transient failures.
        retry_delay_seconds: Delay between retries in seconds.
    """

    name: str
    target_layer: MedallionLayer
    target_table: str
    target_schema: StructType
    source_layer: MedallionLayer | None = None
    quality_checks_path: str = ""
    critical_checks: list[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay_seconds: int = 60

    @property
    def full_table_name(self) -> str:
        """Full Iceberg table name: lakehouse.{layer}.{table}."""
        return f"lakehouse.{self.target_layer.value}.{self.target_table}"

    @property
    def source_table_name(self) -> str | None:
        """Full Iceberg source table name if source_layer is set."""
        if self.source_layer is None:
            return None
        return f"lakehouse.{self.source_layer.value}.{self.target_table}"


class BasePipeline(ABC):
    """Abstract base class for all medallion ETL pipelines.

    Enforces the contract: extract -> transform -> validate_schema -> write.
    Subclasses MUST implement extract() and transform(). Schema validation
    and quality gates are built into the execute() orchestration and cannot
    be bypassed.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        config: PipelineConfig defining target layer, table, and schema.
    """

    def __init__(self, spark: SparkSession, config: PipelineConfig) -> None:
        self.spark = spark
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{config.name}")

    @abstractmethod
    def extract(self) -> DataFrame:
        """Extract source data and return as DataFrame.

        Returns:
            PySpark DataFrame with raw source data.
        """

    @abstractmethod
    def transform(self, df: DataFrame) -> DataFrame:
        """Transform the extracted DataFrame.

        Args:
            df: Input DataFrame from extract().

        Returns:
            Transformed PySpark DataFrame ready for schema validation.
        """

    def validate_schema(self, df: DataFrame) -> bool:
        """Validate DataFrame schema against the target schema.

        Compares field names and types. Allows nullable differences.
        Extra columns in the DataFrame are accepted (additive is OK).

        Args:
            df: DataFrame to validate.

        Returns:
            True if all target fields are present with correct types.
        """
        target_fields = {f.name: f.dataType for f in self.config.target_schema.fields}
        actual_fields = {f.name: f.dataType for f in df.schema.fields}

        for field_name, expected_type in target_fields.items():
            if field_name not in actual_fields:
                self.logger.error("Missing field: %s", field_name)
                return False
            if actual_fields[field_name] != expected_type:
                self.logger.error(
                    "Type mismatch for %s: expected %s, got %s",
                    field_name,
                    expected_type,
                    actual_fields[field_name],
                )
                return False

        return True

    def add_metadata_columns(
        self, df: DataFrame, source_system: str, batch_id: str
    ) -> DataFrame:
        """Add Bronze-layer metadata columns to a DataFrame.

        Adds:
        - source_system: Literal string identifying the data source
        - ingestion_ts: Current timestamp at ingestion time
        - batch_id: Literal string identifying the ingestion batch

        Args:
            df: Input DataFrame.
            source_system: Source system identifier (e.g., "trading_platform").
            batch_id: Batch identifier (e.g., "batch-20260313-001").

        Returns:
            DataFrame with metadata columns appended.
        """
        df = df.withColumn("source_system", lit(source_system))
        df = df.withColumn("ingestion_ts", current_timestamp())
        df = df.withColumn("batch_id", lit(batch_id))
        return df

    def write(self, df: DataFrame) -> None:
        """Write validated DataFrame to the target Iceberg table.

        Uses append mode via df.writeTo().append().

        Args:
            df: Validated DataFrame to write.
        """
        table_name = self.config.full_table_name
        self.logger.info("Writing to %s", table_name)
        df.writeTo(table_name).append()

    def run_quality_checks(self, df: DataFrame) -> dict[str, Any]:
        """Run data quality checks on the DataFrame.

        Placeholder implementation returning passing results.
        Real Soda Core integration comes in Plan 04.

        Args:
            df: DataFrame to check.

        Returns:
            Dict with passed (bool), critical_failures (list), warnings (list).
        """
        return {"passed": True, "critical_failures": [], "warnings": []}

    def execute(self) -> dict[str, Any]:
        """Orchestrate the full pipeline: extract -> transform -> validate -> write.

        Raises:
            SchemaValidationError: If the transformed DataFrame doesn't match target schema.
            QualityGateError: If critical quality checks fail.

        Returns:
            Dict with rows_written count and quality check results.
        """
        self.logger.info("Starting pipeline: %s", self.config.name)

        # 1. Extract
        df = self.extract()
        self.logger.info("Extracted DataFrame")

        # 2. Transform
        df = self.transform(df)
        self.logger.info("Transformed DataFrame")

        # 3. Validate schema
        if not self.validate_schema(df):
            raise SchemaValidationError(
                f"Schema validation failed for pipeline '{self.config.name}'. "
                f"DataFrame schema does not match target schema for "
                f"{self.config.full_table_name}."
            )
        self.logger.info("Schema validation passed")

        # 4. Quality checks
        qc_results = self.run_quality_checks(df)
        if qc_results.get("critical_failures"):
            raise QualityGateError(
                f"Critical quality checks failed for pipeline '{self.config.name}': "
                f"{qc_results['critical_failures']}"
            )
        self.logger.info("Quality checks passed")

        # 5. Write
        row_count = df.count()
        self.write(df)
        self.logger.info("Wrote %d rows to %s", row_count, self.config.full_table_name)

        return {"rows_written": row_count, "quality": qc_results}

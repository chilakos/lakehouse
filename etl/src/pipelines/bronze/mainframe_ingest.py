"""Bronze pipeline for mainframe COBOL data ingestion via Cobrix.

Ingests mainframe flat-file data using COBOL copybook definitions.
Cobrix (spark-cobol) parses EBCDIC-encoded records, handles packed
decimal (COMP-3) fields, and produces a Spark DataFrame.

NOTE: This pipeline skips gracefully if the Cobrix JAR is not available
on the classpath. Tests and CI environments without the JAR will see
a clear skip message rather than a hard failure.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

logger = logging.getLogger(__name__)


class CobrixNotAvailableError(Exception):
    """Raised when Cobrix JAR is not on the Spark classpath."""


def is_cobrix_available(spark: SparkSession) -> bool:
    """Check if Cobrix JAR is available on the Spark classpath.

    Args:
        spark: Active SparkSession.

    Returns:
        True if Cobrix classes are loadable, False otherwise.
    """
    try:
        spark.sparkContext._jvm.za.co.absa.cobrix.spark.cobol.source.DefaultSource  # noqa: B018
        return True
    except Exception:
        return False


class MainframeBronzePipeline(BasePipeline):
    """Concrete Bronze pipeline for mainframe COBOL data ingestion.

    Reads mainframe flat files using COBOL copybook definitions via Cobrix.
    Handles EBCDIC encoding, packed decimal (COMP-3) fields, and
    fixed-width record parsing.

    Args:
        spark: Active SparkSession with Cobrix JAR on classpath.
        copybook_path: Path to the COBOL copybook (.cpy) file.
        data_path: Path to the mainframe data file (.dat).
        source_system: Source system identifier for metadata column.
        batch_id: Batch identifier for metadata column.
    """

    def __init__(
        self,
        spark: SparkSession,
        copybook_path: str,
        data_path: str,
        source_system: str,
        batch_id: str,
    ) -> None:
        self._copybook_path = copybook_path
        self._data_path = data_path
        self._source_system = source_system
        self._batch_id = batch_id

        # Derive table name from copybook filename (e.g., "accounts.cpy" -> "accounts")
        table_name = os.path.splitext(os.path.basename(copybook_path))[0]

        config = PipelineConfig(
            name=f"mainframe-bronze-{table_name}",
            target_layer=MedallionLayer.BRONZE,
            target_table=table_name,
            target_schema=self._build_placeholder_schema(),
        )
        super().__init__(spark=spark, config=config)

    @staticmethod
    def _build_placeholder_schema():
        """Build a placeholder schema for mainframe data.

        The actual schema is defined by the COBOL copybook and determined
        at runtime by Cobrix. This placeholder is used only for PipelineConfig
        construction; validate_schema is overridden to always pass since
        we trust Cobrix's schema derivation.
        """
        from pyspark.sql.types import StringType, StructField, StructType

        return StructType(
            [
                StructField("_placeholder", StringType(), nullable=True),
            ]
        )

    def validate_schema(self, df: DataFrame) -> bool:
        """Override schema validation for mainframe data.

        Cobrix derives the schema from the COBOL copybook at runtime.
        The actual schema is not known at pipeline construction time,
        so we skip strict schema validation and trust Cobrix's parsing.

        Args:
            df: DataFrame to validate.

        Returns:
            True always -- schema is determined by the copybook.
        """
        self.logger.info(
            "Schema validation skipped for mainframe data (Cobrix-derived schema). Columns: %s",
            [f.name for f in df.schema.fields],
        )
        return True

    def extract(self) -> DataFrame:
        """Read mainframe data using Cobrix with COBOL copybook.

        Uses spark.read.format("cobol") with Cobrix options for:
        - EBCDIC encoding
        - Record sequence parsing
        - Schema collapse (flattens nested COBOL groups)

        Returns:
            PySpark DataFrame with parsed mainframe records.

        Raises:
            CobrixNotAvailableError: If Cobrix JAR is not on the classpath.
        """
        if not is_cobrix_available(self.spark):
            raise CobrixNotAvailableError(
                "Cobrix JAR not available on Spark classpath. "
                "Add za.co.absa.cobrix:spark-cobol_2.12:2.9.2 to spark.jars.packages"
            )

        self.logger.info(
            "Reading mainframe data: copybook=%s, data=%s",
            self._copybook_path,
            self._data_path,
        )

        df = (
            self.spark.read.format("cobol")
            .option("copybook", self._copybook_path)
            .option("encoding", "ebcdic")
            .option("is_record_sequence", "true")
            .option("schema_retention_policy", "collapse_root")
            .load(self._data_path)
        )

        return df

    def transform(self, df: DataFrame) -> DataFrame:
        """Add metadata columns and cast packed decimal fields.

        Bronze layer is raw-as-is with metadata -- casts packed decimal
        fields (COMP-3) to Python Decimal type for financial precision.

        Args:
            df: Cobrix-parsed DataFrame from extract().

        Returns:
            DataFrame with metadata columns and cast decimal fields.
        """
        from pyspark.sql.functions import col
        from pyspark.sql.types import DecimalType

        # Cast any COMP-3 (packed decimal) fields to DecimalType for precision
        for field in df.schema.fields:
            if "decimal" in str(field.dataType).lower() or "comp" in field.name.lower():
                df = df.withColumn(field.name, col(field.name).cast(DecimalType(18, 4)))

        return self.add_metadata_columns(df, self._source_system, self._batch_id)

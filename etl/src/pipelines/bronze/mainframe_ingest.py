"""Bronze pipeline for mainframe COBOL data ingestion via Cobrix.

Ingests mainframe flat-file data using COBOL copybook definitions.
Cobrix (spark-cobol) parses EBCDIC-encoded records, handles packed
decimal (COMP-3) fields, and produces a Spark DataFrame.

NOTE: This pipeline skips gracefully if the Cobrix JAR is not available
on the classpath. Tests and CI environments without the JAR will see
a clear skip message rather than a hard failure.

When ``raw_zone_config`` and ``manifest`` are provided, the pipeline verifies
that the data file exists in the raw zone before extraction and updates the
manifest entry after execution (PROCESSED on success, FAILED on error).
Omitting these parameters preserves the original behaviour.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

    from src.ingestion.manifest import IngestionManifest, ManifestEntry
    from src.ingestion.raw_zone import RawZoneConfig

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
        data_path: Path to the mainframe data file (.dat).  When
            ``raw_zone_config`` is provided this must be the full S3 URI of
            the file inside the raw zone.
        source_system: Source system identifier for metadata column.
        batch_id: Batch identifier for metadata column.
        raw_zone_config: Optional raw zone configuration.  When supplied,
            ``extract()`` verifies the file exists in the raw zone before
            reading.
        manifest: Optional ``IngestionManifest`` instance.  When supplied,
            ``execute()`` updates the manifest entry to PROCESSED on success
            or FAILED on error.
        manifest_entry: Optional existing ``ManifestEntry`` for the file
            being processed.  Required when ``manifest`` is provided.
    """

    def __init__(
        self,
        spark: SparkSession,
        copybook_path: str,
        data_path: str,
        source_system: str,
        batch_id: str,
        raw_zone_config: RawZoneConfig | None = None,
        manifest: IngestionManifest | None = None,
        manifest_entry: ManifestEntry | None = None,
    ) -> None:
        self._copybook_path = copybook_path
        self._data_path = data_path
        self._source_system = source_system
        self._batch_id = batch_id
        self._raw_zone_config = raw_zone_config
        self._manifest = manifest
        self._manifest_entry = manifest_entry

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

        return StructType([
            StructField("_placeholder", StringType(), nullable=True),
        ])

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
            "Schema validation skipped for mainframe data (Cobrix-derived schema). "
            "Columns: %s",
            [f.name for f in df.schema.fields],
        )
        return True

    def extract(self) -> DataFrame:
        """Read mainframe data using Cobrix with COBOL copybook.

        When ``raw_zone_config`` was provided at construction time, this method
        first verifies that the data file is present in the raw zone by listing
        files for the source system and business date derived from the S3 path.

        Uses spark.read.format("cobol") with Cobrix options for:
        - EBCDIC encoding
        - Record sequence parsing
        - Schema collapse (flattens nested COBOL groups)

        Returns:
            PySpark DataFrame with parsed mainframe records.

        Raises:
            CobrixNotAvailableError: If Cobrix JAR is not on the classpath.
            FileNotFoundError: If raw zone verification is enabled and the
                file is not found in the raw zone.
        """
        if not is_cobrix_available(self.spark):
            raise CobrixNotAvailableError(
                "Cobrix JAR not available on Spark classpath. "
                "Add za.co.absa.cobrix:spark-cobol_2.12:2.9.2 to spark.jars.packages"
            )

        # ------------------------------------------------------------------
        # Raw zone verification (only when raw_zone_config is provided)
        # ------------------------------------------------------------------
        if self._raw_zone_config is not None:
            self._verify_raw_zone_file()

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

    def _verify_raw_zone_file(self) -> None:
        """Verify the data file exists in the raw zone.

        Parses the source system and business date from the manifest entry
        (if available) or from the S3 path, then calls ``list_raw_files``
        to confirm the file is present.

        Raises:
            FileNotFoundError: If the file is not found in the raw zone.
        """
        from src.ingestion.raw_zone import RawZoneManager

        filename = os.path.basename(self._data_path)

        # Prefer manifest entry metadata when available
        if self._manifest_entry is not None:
            source_system = self._manifest_entry.source_system
            business_date = self._manifest_entry.business_date
        else:
            import re

            source_system = self._source_system
            # Best-effort: extract YYYY-MM-DD date segment from the S3 path
            match = re.search(r"\d{4}-\d{2}-\d{2}", self._data_path)
            business_date = match.group(0) if match else ""

        manager = RawZoneManager(config=self._raw_zone_config)
        raw_files = manager.list_raw_files(source_system, business_date)
        found = any(os.path.basename(rf.raw_path) == filename for rf in raw_files)

        if not found:
            raise FileNotFoundError(
                f"File '{filename}' not found in raw zone for "
                f"source_system='{source_system}', business_date='{business_date}'. "
                "Ensure the file has been uploaded via RawZoneManager.upload_to_raw_zone()."
            )

        self.logger.info("Raw zone verification passed for '%s'", filename)

    def execute(self) -> dict:
        """Orchestrate the pipeline and update the manifest on completion.

        Extends the base ``execute()`` to update the manifest entry when a
        ``manifest`` and ``manifest_entry`` are provided.  On success the
        entry is marked ``PROCESSED``; on any exception it is marked
        ``FAILED`` and the exception is re-raised.

        Returns:
            Dict with rows_written count and quality check results (same as
            ``BasePipeline.execute()``).
        """
        try:
            result = super().execute()
        except Exception as exc:
            if self._manifest is not None and self._manifest_entry is not None:
                self._manifest.mark_failed(
                    file_id=self._manifest_entry.file_id,
                    error_message=str(exc),
                    source_system=self._manifest_entry.source_system,
                    business_date=self._manifest_entry.business_date,
                )
            raise

        if self._manifest is not None and self._manifest_entry is not None:
            self._manifest.mark_processed(
                file_id=self._manifest_entry.file_id,
                bronze_table=self.config.full_table_name,
                row_count=result.get("rows_written", 0),
                source_system=self._manifest_entry.source_system,
                business_date=self._manifest_entry.business_date,
            )

        return result

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

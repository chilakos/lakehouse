"""Bronze pipeline for trades ingestion.

Ingests raw trade data with metadata columns (source_system, ingestion_ts,
batch_id). No transformation -- raw-as-is per locked decision. Maximum
traceability, no data loss.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.types import StructType


class TradesBronzePipeline(BasePipeline):
    """Concrete Bronze pipeline for trades ingestion.

    Accepts raw trade data (list of dicts or DataFrame), adds metadata columns,
    and writes to lakehouse.bronze.trades.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        source_data: Raw trade records as list of dicts.
        source_system: Source system identifier for metadata column.
        batch_id: Batch identifier for metadata column.
    """

    def __init__(
        self,
        spark: SparkSession,
        source_data: list[dict],
        source_system: str,
        batch_id: str,
    ) -> None:
        self._source_data = source_data
        self._source_system = source_system
        self._batch_id = batch_id

        config = PipelineConfig(
            name="trades-bronze",
            target_layer=MedallionLayer.BRONZE,
            target_table="trades",
            target_schema=self._build_bronze_schema(),
        )
        super().__init__(spark=spark, config=config)

    @staticmethod
    def _build_bronze_schema() -> StructType:
        """Build the Bronze trades schema: base trades + metadata columns."""
        from pyspark.sql.types import StringType, StructField, TimestampType

        from src.synthetic.generators import trades_schema

        base = trades_schema()
        metadata_fields = [
            StructField("source_system", StringType(), nullable=True),
            StructField("ingestion_ts", TimestampType(), nullable=True),
            StructField("batch_id", StringType(), nullable=True),
        ]
        return base.add(metadata_fields[0]).add(metadata_fields[1]).add(metadata_fields[2])

    def extract(self) -> DataFrame:
        """Create DataFrame from source trade data.

        Returns:
            PySpark DataFrame with raw trade fields (no metadata yet).
        """
        from src.synthetic.generators import trades_schema

        return self.spark.createDataFrame(self._source_data, trades_schema())

    def transform(self, df: DataFrame) -> DataFrame:
        """Add metadata columns to raw trade DataFrame.

        Bronze layer is raw-as-is -- only adds source_system, ingestion_ts,
        batch_id metadata columns. No other transformation.

        Args:
            df: Raw trades DataFrame from extract().

        Returns:
            DataFrame with metadata columns appended.
        """
        return self.add_metadata_columns(df, self._source_system, self._batch_id)

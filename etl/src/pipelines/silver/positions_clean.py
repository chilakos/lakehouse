"""Silver pipeline for positions cleaning and deduplication.

Reads from Bronze positions, deduplicates by position_id per as_of_date
(keeps latest ingestion), drops Bronze metadata columns, validates
market_value > 0. Produces entity-centric output: one row per position
per as_of_date.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession


class PositionsSilverPipeline(BasePipeline):
    """Concrete Silver pipeline for positions cleaning and deduplication.

    Reads from Bronze positions table, deduplicates by position_id per
    as_of_date, removes Bronze metadata columns, and applies business
    rule filters (market_value > 0).

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        source_table: Full Iceberg table name for the Bronze source
                      (e.g., "lakehouse.bronze.positions").
    """

    def __init__(
        self,
        spark: SparkSession,
        source_table: str = "lakehouse.bronze.positions",
    ) -> None:
        self._source_table = source_table

        config = PipelineConfig(
            name="positions-silver",
            source_layer=MedallionLayer.BRONZE,
            target_layer=MedallionLayer.SILVER,
            target_table="positions",
            target_schema=self._build_silver_schema(),
        )
        super().__init__(spark=spark, config=config)

    @staticmethod
    def _build_silver_schema():
        """Build the Silver positions schema: base positions without metadata."""
        from src.synthetic.generators import positions_schema

        return positions_schema()

    def extract(self) -> DataFrame:
        """Read raw positions from Bronze layer.

        Returns:
            PySpark DataFrame with all Bronze columns (including metadata).
        """
        return self.spark.table(self._source_table)

    def transform(self, df: DataFrame) -> DataFrame:
        """Clean and deduplicate positions.

        Steps:
        1. Deduplicate by position_id + as_of_date (keep row with latest ingestion_ts)
        2. Drop Bronze metadata columns (source_system, ingestion_ts, batch_id)
        3. Filter: market_value > 0 (business rule)

        Args:
            df: Raw Bronze positions DataFrame.

        Returns:
            Cleaned, deduplicated DataFrame without metadata columns.
        """
        from pyspark.sql import Window
        from pyspark.sql.functions import col, row_number

        # 1. Deduplicate by position_id + as_of_date, keep most recent ingestion_ts
        window = Window.partitionBy("position_id", "as_of_date").orderBy(
            col("ingestion_ts").desc()
        )
        deduped = df.withColumn("_row_num", row_number().over(window))
        deduped = deduped.filter(col("_row_num") == 1).drop("_row_num")

        # 2. Drop Bronze metadata columns
        cleaned = deduped.drop("source_system", "ingestion_ts", "batch_id")

        # 3. Apply business rules
        filtered = cleaned.filter(col("market_value") > 0)

        return filtered

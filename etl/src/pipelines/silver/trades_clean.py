"""Silver pipeline for trades cleaning and deduplication.

Reads from Bronze trades, deduplicates by trade_id (keeps latest ingestion),
drops Bronze metadata columns, applies business rules (price > 0, quantity > 0).
Produces entity-centric output: one row per trade_id.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession


class TradesSilverPipeline(BasePipeline):
    """Concrete Silver pipeline for trades cleaning and deduplication.

    Reads from Bronze trades table, deduplicates by trade_id, removes
    Bronze metadata columns, and applies business rule filters.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        source_table: Full Iceberg table name for the Bronze source
                      (e.g., "lakehouse.bronze.trades").
    """

    def __init__(
        self,
        spark: SparkSession,
        source_table: str = "lakehouse.bronze.trades",
    ) -> None:
        self._source_table = source_table

        config = PipelineConfig(
            name="trades-silver",
            source_layer=MedallionLayer.BRONZE,
            target_layer=MedallionLayer.SILVER,
            target_table="trades",
            target_schema=self._build_silver_schema(),
        )
        super().__init__(spark=spark, config=config)

    @staticmethod
    def _build_silver_schema():
        """Build the Silver trades schema: base trades without metadata."""
        from src.synthetic.generators import trades_schema

        return trades_schema()

    def extract(self) -> DataFrame:
        """Read raw trades from Bronze layer.

        Returns:
            PySpark DataFrame with all Bronze columns (including metadata).
        """
        return self.spark.table(self._source_table)

    def transform(self, df: DataFrame) -> DataFrame:
        """Clean and deduplicate trades.

        Steps:
        1. Deduplicate by trade_id (keep row with latest ingestion_ts via window)
        2. Drop Bronze metadata columns (source_system, ingestion_ts, batch_id)
        3. Filter: price > 0 AND quantity > 0 (business rule)

        Args:
            df: Raw Bronze trades DataFrame.

        Returns:
            Cleaned, deduplicated DataFrame without metadata columns.
        """
        from pyspark.sql import Window
        from pyspark.sql.functions import col, row_number

        # 1. Deduplicate by trade_id, keep most recent ingestion_ts
        window = Window.partitionBy("trade_id").orderBy(col("ingestion_ts").desc())
        deduped = df.withColumn("_row_num", row_number().over(window))
        deduped = deduped.filter(col("_row_num") == 1).drop("_row_num")

        # 2. Drop Bronze metadata columns
        cleaned = deduped.drop("source_system", "ingestion_ts", "batch_id")

        # 3. Apply business rules
        filtered = cleaned.filter((col("price") > 0) & (col("quantity") > 0))

        return filtered

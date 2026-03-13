"""Gold pipeline for pre-aggregated trading metrics.

Reads from Silver trades, computes per-symbol/side aggregates:
total_notional, trade_count, avg_price, min_price, max_price.
Pre-aggregated metrics for BI per locked Gold decision.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession


class TradingMetricsGoldPipeline(BasePipeline):
    """Concrete Gold pipeline for pre-aggregated trading metrics.

    Reads from Silver trades table and produces aggregated metrics
    grouped by symbol and side.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        source_table: Full Iceberg table name for the Silver source
                      (e.g., "lakehouse.silver.trades").
    """

    def __init__(
        self,
        spark: SparkSession,
        source_table: str = "lakehouse.silver.trades",
    ) -> None:
        self._source_table = source_table

        config = PipelineConfig(
            name="trading-metrics-gold",
            source_layer=MedallionLayer.SILVER,
            target_layer=MedallionLayer.GOLD,
            target_table="trading_metrics",
            target_schema=self._build_gold_schema(),
        )
        super().__init__(spark=spark, config=config)

    @staticmethod
    def _build_gold_schema():
        """Build the Gold trading metrics schema."""
        from pyspark.sql.types import (
            DecimalType,
            LongType,
            StringType,
            StructField,
            StructType,
        )

        return StructType([
            StructField("symbol", StringType(), nullable=False),
            StructField("side", StringType(), nullable=False),
            StructField("total_notional", DecimalType(38, 4), nullable=True),
            StructField("trade_count", LongType(), nullable=False),
            StructField("avg_price", DecimalType(38, 4), nullable=True),
            StructField("min_price", DecimalType(18, 4), nullable=True),
            StructField("max_price", DecimalType(18, 4), nullable=True),
        ])

    def extract(self) -> DataFrame:
        """Read cleaned trades from Silver layer.

        Returns:
            PySpark DataFrame with Silver trade columns.
        """
        return self.spark.table(self._source_table)

    def transform(self, df: DataFrame) -> DataFrame:
        """Compute per-symbol/side aggregated trading metrics.

        Aggregates:
        - total_notional: sum of notional values
        - trade_count: count of trades
        - avg_price: average price
        - min_price: minimum price
        - max_price: maximum price

        Args:
            df: Silver trades DataFrame.

        Returns:
            Aggregated metrics DataFrame grouped by symbol and side.
        """
        from pyspark.sql.functions import avg, col, count, max as spark_max, min as spark_min, sum as spark_sum

        return (
            df.groupBy("symbol", "side")
            .agg(
                spark_sum("notional").alias("total_notional"),
                count("*").alias("trade_count"),
                avg("price").alias("avg_price"),
                spark_min("price").alias("min_price"),
                spark_max("price").alias("max_price"),
            )
        )

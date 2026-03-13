"""Gold pipeline for aggregated risk exposure metrics.

Reads from Silver positions and Silver risk_metrics, joins by account_id,
and aggregates per account_id/sector/currency: total_market_value,
total_var_95, total_var_99, total_expected_shortfall, position_count.

Pre-aggregated metrics for BI and semantic layer consumption.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession


class RiskExposureGoldPipeline(BasePipeline):
    """Concrete Gold pipeline for aggregated risk exposure metrics.

    Reads from Silver positions and Silver risk_metrics tables, joins
    them by account_id, and produces aggregated risk exposure metrics
    grouped by account_id, sector, and currency.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        positions_table: Full Iceberg table name for the Silver positions source.
        risk_metrics_table: Full Iceberg table name for the Silver risk_metrics source.
    """

    def __init__(
        self,
        spark: SparkSession,
        positions_table: str = "lakehouse.silver.positions",
        risk_metrics_table: str = "lakehouse.silver.risk_metrics",
    ) -> None:
        self._positions_table = positions_table
        self._risk_metrics_table = risk_metrics_table

        config = PipelineConfig(
            name="risk-exposure-gold",
            source_layer=MedallionLayer.SILVER,
            target_layer=MedallionLayer.GOLD,
            target_table="risk_exposure",
            target_schema=self._build_gold_schema(),
        )
        super().__init__(spark=spark, config=config)

    @staticmethod
    def _build_gold_schema():
        """Build the Gold risk exposure schema."""
        from pyspark.sql.types import (
            DecimalType,
            LongType,
            StringType,
            StructField,
            StructType,
        )

        return StructType([
            StructField("account_id", StringType(), nullable=False),
            StructField("sector", StringType(), nullable=False),
            StructField("currency", StringType(), nullable=False),
            StructField("total_market_value", DecimalType(38, 4), nullable=True),
            StructField("total_var_95", DecimalType(18, 2), nullable=True),
            StructField("total_var_99", DecimalType(18, 2), nullable=True),
            StructField("total_expected_shortfall", DecimalType(18, 2), nullable=True),
            StructField("position_count", LongType(), nullable=False),
        ])

    def extract(self) -> DataFrame:
        """Read positions and risk_metrics from Silver layer.

        Returns a joined DataFrame of positions and risk_metrics on account_id.

        Returns:
            PySpark DataFrame with joined position and risk metric columns.
        """
        positions_df = self.spark.table(self._positions_table)
        risk_metrics_df = self.spark.table(self._risk_metrics_table)

        return positions_df.join(
            risk_metrics_df,
            on="account_id",
            how="inner",
        )

    def transform(self, df: DataFrame) -> DataFrame:
        """Aggregate risk exposure metrics per account_id/sector/currency.

        Aggregates:
        - total_market_value: sum of market_value
        - total_var_95: sum of var_95
        - total_var_99: sum of var_99
        - total_expected_shortfall: sum of expected_shortfall
        - position_count: count of positions

        Args:
            df: Joined positions + risk_metrics DataFrame.

        Returns:
            Aggregated risk exposure DataFrame.
        """
        from pyspark.sql.functions import (
            col,
            count,
            sum as spark_sum,
        )

        return (
            df.groupBy("account_id", "sector", "currency")
            .agg(
                spark_sum("market_value").alias("total_market_value"),
                spark_sum("var_95").alias("total_var_95"),
                spark_sum("var_99").alias("total_var_99"),
                spark_sum("expected_shortfall").alias("total_expected_shortfall"),
                count("*").alias("position_count"),
            )
        )

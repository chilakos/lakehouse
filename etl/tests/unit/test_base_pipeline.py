"""Unit tests for BasePipeline contract enforcement.

Tests the abstract base class behavior:
- ABC enforcement (cannot instantiate directly)
- execute() orchestration order
- Schema validation integration with execute()
- Quality gate integration with execute()
- Metadata column addition for Bronze layer
- MedallionLayer enum values
- PipelineConfig namespace mapping
"""

from unittest.mock import MagicMock, patch, call

import pytest


@pytest.mark.unit
class TestBasePipelineABC:
    """Test that BasePipeline enforces abstract method contract."""

    def test_cannot_instantiate_directly(self):
        """BasePipeline cannot be instantiated -- it's an ABC."""
        from src.pipelines.base import BasePipeline

        with pytest.raises(TypeError):
            BasePipeline(spark=MagicMock(), config=MagicMock())

    def test_concrete_subclass_can_be_instantiated(self):
        """A subclass implementing extract() and transform() can be created."""
        from pyspark.sql.types import IntegerType, StringType, StructField, StructType

        from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

        class ConcretePipeline(BasePipeline):
            def extract(self):
                return MagicMock()

            def transform(self, df):
                return df

        config = PipelineConfig(
            name="test",
            target_layer=MedallionLayer.BRONZE,
            target_table="test_table",
            target_schema=StructType([
                StructField("id", IntegerType(), nullable=False),
                StructField("name", StringType(), nullable=True),
            ]),
        )
        pipeline = ConcretePipeline(spark=MagicMock(), config=config)
        assert pipeline is not None


@pytest.mark.unit
class TestExecuteOrchestration:
    """Test that execute() calls methods in the correct order."""

    def _make_pipeline(self):
        """Create a concrete pipeline with mocked methods for order testing."""
        from pyspark.sql.types import IntegerType, StringType, StructField, StructType

        from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

        call_order = []

        class OrderTrackingPipeline(BasePipeline):
            def extract(self):
                call_order.append("extract")
                mock_df = MagicMock()
                mock_df.count.return_value = 5
                return mock_df

            def transform(self, df):
                call_order.append("transform")
                return df

        config = PipelineConfig(
            name="order-test",
            target_layer=MedallionLayer.SILVER,
            target_table="test_table",
            target_schema=StructType([
                StructField("id", IntegerType(), nullable=False),
                StructField("name", StringType(), nullable=True),
            ]),
        )

        pipeline = OrderTrackingPipeline(spark=MagicMock(), config=config)
        # Mock validate_schema to return True (happy path)
        pipeline.validate_schema = MagicMock(side_effect=lambda df: (call_order.append("validate_schema"), True)[1])
        pipeline.run_quality_checks = MagicMock(
            side_effect=lambda df: (
                call_order.append("run_quality_checks"),
                {"passed": True, "critical_failures": [], "warnings": []},
            )[1]
        )
        pipeline.write = MagicMock(side_effect=lambda df: call_order.append("write"))

        return pipeline, call_order

    def test_execute_calls_in_order(self):
        """execute() calls extract -> transform -> validate_schema -> write in order."""
        pipeline, call_order = self._make_pipeline()
        pipeline.execute()
        assert call_order == ["extract", "transform", "validate_schema", "run_quality_checks", "write"]

    def test_execute_returns_result_dict(self):
        """execute() returns dict with rows_written and quality keys."""
        pipeline, _ = self._make_pipeline()
        result = pipeline.execute()
        assert "rows_written" in result
        assert "quality" in result
        assert result["rows_written"] == 5

    def test_execute_raises_schema_validation_error_on_mismatch(self):
        """execute() raises SchemaValidationError when validate_schema returns False."""
        from src.pipelines.base import SchemaValidationError

        pipeline, _ = self._make_pipeline()
        pipeline.validate_schema = MagicMock(return_value=False)

        with pytest.raises(SchemaValidationError):
            pipeline.execute()

    def test_execute_raises_quality_gate_error_on_critical_failures(self):
        """execute() raises QualityGateError when critical quality checks fail."""
        from src.pipelines.base import QualityGateError

        pipeline, _ = self._make_pipeline()
        pipeline.run_quality_checks = MagicMock(
            return_value={"passed": False, "critical_failures": ["null_pk"], "warnings": []}
        )

        with pytest.raises(QualityGateError):
            pipeline.execute()


@pytest.mark.unit
class TestMetadataColumns:
    """Test add_metadata_columns for Bronze layer."""

    @patch("src.pipelines.base.current_timestamp")
    @patch("src.pipelines.base.lit")
    def test_add_metadata_columns_adds_required_fields(self, mock_lit, mock_ts):
        """add_metadata_columns adds source_system, ingestion_ts, batch_id columns."""
        from pyspark.sql.types import IntegerType, StringType, StructField, StructType

        from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

        class MetadataTestPipeline(BasePipeline):
            def extract(self):
                return MagicMock()

            def transform(self, df):
                return df

        config = PipelineConfig(
            name="metadata-test",
            target_layer=MedallionLayer.BRONZE,
            target_table="test_table",
            target_schema=StructType([
                StructField("id", IntegerType(), nullable=False),
            ]),
        )

        pipeline = MetadataTestPipeline(spark=MagicMock(), config=config)

        # Mock the DataFrame and withColumn chain
        mock_df = MagicMock()
        mock_df.withColumn.return_value = mock_df

        result = pipeline.add_metadata_columns(mock_df, "test_source", "batch-001")
        # withColumn should have been called 3 times (source_system, ingestion_ts, batch_id)
        assert mock_df.withColumn.call_count == 3
        call_args = [c[0][0] for c in mock_df.withColumn.call_args_list]
        assert "source_system" in call_args
        assert "ingestion_ts" in call_args
        assert "batch_id" in call_args


@pytest.mark.unit
class TestMedallionLayer:
    """Test MedallionLayer enum values."""

    def test_medallion_layer_has_bronze_silver_gold(self):
        """MedallionLayer enum has BRONZE, SILVER, GOLD values."""
        from src.pipelines.base import MedallionLayer

        assert MedallionLayer.BRONZE.value == "bronze"
        assert MedallionLayer.SILVER.value == "silver"
        assert MedallionLayer.GOLD.value == "gold"


@pytest.mark.unit
class TestPipelineConfig:
    """Test PipelineConfig namespace mapping."""

    def test_config_maps_bronze_to_namespace(self):
        """PipelineConfig target_layer BRONZE maps to lakehouse.bronze.{table}."""
        from pyspark.sql.types import IntegerType, StructField, StructType

        from src.pipelines.base import MedallionLayer, PipelineConfig

        config = PipelineConfig(
            name="ns-test",
            target_layer=MedallionLayer.BRONZE,
            target_table="trades",
            target_schema=StructType([StructField("id", IntegerType())]),
        )
        assert config.full_table_name == "lakehouse.bronze.trades"

    def test_config_maps_silver_to_namespace(self):
        """PipelineConfig target_layer SILVER maps to lakehouse.silver.{table}."""
        from pyspark.sql.types import IntegerType, StructField, StructType

        from src.pipelines.base import MedallionLayer, PipelineConfig

        config = PipelineConfig(
            name="ns-test",
            target_layer=MedallionLayer.SILVER,
            target_table="trades",
            target_schema=StructType([StructField("id", IntegerType())]),
        )
        assert config.full_table_name == "lakehouse.silver.trades"

    def test_config_maps_gold_to_namespace(self):
        """PipelineConfig target_layer GOLD maps to lakehouse.gold.{table}."""
        from pyspark.sql.types import IntegerType, StructField, StructType

        from src.pipelines.base import MedallionLayer, PipelineConfig

        config = PipelineConfig(
            name="ns-test",
            target_layer=MedallionLayer.GOLD,
            target_table="trading_metrics",
            target_schema=StructType([StructField("id", IntegerType())]),
        )
        assert config.full_table_name == "lakehouse.gold.trading_metrics"

"""Unit tests for schema validation accept/reject behavior.

Tests the validate_schema method of BasePipeline:
- Matching schema passes validation
- Missing column fails validation
- Wrong column type fails validation
- Extra columns in DataFrame are accepted (additive is OK)
"""

from unittest.mock import MagicMock

import pytest


def _make_pipeline_with_schema(target_schema):
    """Helper: create a concrete pipeline with a given target schema."""
    from src.pipelines.base import BasePipeline, MedallionLayer, PipelineConfig

    class SchemaTestPipeline(BasePipeline):
        def extract(self):
            return MagicMock()

        def transform(self, df):
            return df

    config = PipelineConfig(
        name="schema-test",
        target_layer=MedallionLayer.BRONZE,
        target_table="test_table",
        target_schema=target_schema,
    )
    return SchemaTestPipeline(spark=MagicMock(), config=config)


@pytest.mark.unit
class TestSchemaValidation:
    """Test validate_schema logic for field name and type comparison."""

    def test_matching_schema_passes(self):
        """validate_schema returns True when DataFrame schema matches target."""
        from pyspark.sql.types import IntegerType, StringType, StructField, StructType

        target = StructType([
            StructField("id", IntegerType(), nullable=False),
            StructField("name", StringType(), nullable=True),
        ])

        pipeline = _make_pipeline_with_schema(target)

        # Mock df with matching schema
        mock_df = MagicMock()
        mock_df.schema = StructType([
            StructField("id", IntegerType(), nullable=True),  # nullable difference OK
            StructField("name", StringType(), nullable=True),
        ])

        assert pipeline.validate_schema(mock_df) is True

    def test_missing_column_fails(self):
        """validate_schema returns False when DataFrame has missing columns."""
        from pyspark.sql.types import IntegerType, StringType, StructField, StructType

        target = StructType([
            StructField("id", IntegerType(), nullable=False),
            StructField("name", StringType(), nullable=True),
        ])

        pipeline = _make_pipeline_with_schema(target)

        # Mock df missing "name" column
        mock_df = MagicMock()
        mock_df.schema = StructType([
            StructField("id", IntegerType(), nullable=False),
        ])

        assert pipeline.validate_schema(mock_df) is False

    def test_wrong_type_fails(self):
        """validate_schema returns False when DataFrame has wrong column types."""
        from pyspark.sql.types import IntegerType, StringType, StructField, StructType

        target = StructType([
            StructField("id", IntegerType(), nullable=False),
            StructField("name", StringType(), nullable=True),
        ])

        pipeline = _make_pipeline_with_schema(target)

        # Mock df with "name" as IntegerType instead of StringType
        mock_df = MagicMock()
        mock_df.schema = StructType([
            StructField("id", IntegerType(), nullable=False),
            StructField("name", IntegerType(), nullable=True),  # wrong type
        ])

        assert pipeline.validate_schema(mock_df) is False

    def test_extra_columns_accepted(self):
        """validate_schema returns True when DataFrame has extra columns (additive OK)."""
        from pyspark.sql.types import IntegerType, StringType, StructField, StructType

        target = StructType([
            StructField("id", IntegerType(), nullable=False),
        ])

        pipeline = _make_pipeline_with_schema(target)

        # Mock df with extra "name" column
        mock_df = MagicMock()
        mock_df.schema = StructType([
            StructField("id", IntegerType(), nullable=False),
            StructField("name", StringType(), nullable=True),  # extra column
        ])

        assert pipeline.validate_schema(mock_df) is True

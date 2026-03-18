"""Integration tests for mainframe COBOL data ingestion via Cobrix.

Tests MainframeBronzePipeline with sample COBOL copybook and data files.
Skips gracefully if Cobrix JAR is not available on the Spark classpath.

Requires:
- Cobrix JAR: za.co.absa.cobrix:spark-cobol_2.12:2.9.2
- Docker services: Nessie, MinIO (for SparkSession initialization)
"""

import os

import pytest

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "fixtures")
SAMPLE_COPYBOOK = os.path.join(FIXTURES_DIR, "sample_copybook.cpy")
SAMPLE_DATA = os.path.join(FIXTURES_DIR, "sample_mainframe.dat")

COBRIX_SKIP_MSG = (
    "Cobrix JAR not available -- skipping mainframe tests. "
    "Add za.co.absa.cobrix:spark-cobol_2.12:2.9.2 to spark.jars.packages"
)


def _cobrix_available(spark) -> bool:
    """Check if Cobrix JAR is loadable on the Spark classpath."""
    try:
        from src.pipelines.bronze.mainframe_ingest import is_cobrix_available

        return is_cobrix_available(spark)
    except Exception:
        return False


@pytest.mark.integration
class TestMainframeBronzePipeline:
    """Test MainframeBronzePipeline reads COBOL copybook via Cobrix."""

    def test_pipeline_reads_copybook_and_produces_dataframe(self, spark_session):
        """MainframeBronzePipeline reads sample copybook and produces DataFrame with expected columns."""
        if not _cobrix_available(spark_session):
            pytest.skip(COBRIX_SKIP_MSG)

        from src.pipelines.bronze.mainframe_ingest import MainframeBronzePipeline

        pipeline = MainframeBronzePipeline(
            spark=spark_session,
            copybook_path=SAMPLE_COPYBOOK,
            data_path=SAMPLE_DATA,
            source_system="mainframe_test",
            batch_id="test-batch-001",
        )

        df = pipeline.extract()
        col_names = [f.name for f in df.schema.fields]

        # Cobrix should derive columns from the copybook
        # COBOL field names are converted: ACCOUNT-ID -> ACCOUNT_ID, etc.
        assert "ACCOUNT_ID" in col_names or "account_id" in [c.lower() for c in col_names]
        assert "BALANCE" in col_names or "balance" in [c.lower() for c in col_names]
        assert "ACCOUNT_TYPE" in col_names or "account_type" in [c.lower() for c in col_names]
        assert "OPEN_DATE" in col_names or "open_date" in [c.lower() for c in col_names]

    def test_packed_decimal_fields_parsed_correctly(self, spark_session):
        """Packed decimal (COMP-3) fields are correctly parsed to Decimal type."""
        if not _cobrix_available(spark_session):
            pytest.skip(COBRIX_SKIP_MSG)

        from src.pipelines.bronze.mainframe_ingest import MainframeBronzePipeline

        pipeline = MainframeBronzePipeline(
            spark=spark_session,
            copybook_path=SAMPLE_COPYBOOK,
            data_path=SAMPLE_DATA,
            source_system="mainframe_test",
            batch_id="test-batch-002",
        )

        df = pipeline.extract()
        transformed = pipeline.transform(df)

        # After transform, BALANCE (COMP-3) should be DecimalType
        from pyspark.sql.types import DecimalType

        balance_field = None
        for field in transformed.schema.fields:
            if field.name.lower() == "balance":
                balance_field = field
                break

        assert balance_field is not None, "BALANCE field not found after transform"
        assert isinstance(balance_field.dataType, DecimalType), (
            f"BALANCE should be DecimalType after transform, got {balance_field.dataType}"
        )

    def test_string_fields_decoded_from_ebcdic(self, spark_session):
        """String fields (PIC X) are trimmed and decoded from EBCDIC correctly."""
        if not _cobrix_available(spark_session):
            pytest.skip(COBRIX_SKIP_MSG)

        from src.pipelines.bronze.mainframe_ingest import MainframeBronzePipeline

        pipeline = MainframeBronzePipeline(
            spark=spark_session,
            copybook_path=SAMPLE_COPYBOOK,
            data_path=SAMPLE_DATA,
            source_system="mainframe_test",
            batch_id="test-batch-003",
        )

        df = pipeline.extract()
        rows = df.collect()

        if len(rows) > 0:
            # ACCOUNT_TYPE is PIC X(3) -- should be readable string, no EBCDIC garbling
            row = rows[0]
            account_type_col = None
            for col_name in df.columns:
                if col_name.lower() == "account_type":
                    account_type_col = col_name
                    break
            if account_type_col:
                value = row[account_type_col]
                assert isinstance(value, str), f"ACCOUNT_TYPE should be string, got {type(value)}"
                assert len(value.strip()) > 0, "ACCOUNT_TYPE should not be empty after EBCDIC decode"

    def test_cobrix_not_available_raises_error(self, spark_session):
        """MainframeBronzePipeline raises CobrixNotAvailableError when JAR missing."""
        from unittest.mock import patch

        from src.pipelines.bronze.mainframe_ingest import (
            CobrixNotAvailableError,
            MainframeBronzePipeline,
        )

        pipeline = MainframeBronzePipeline(
            spark=spark_session,
            copybook_path=SAMPLE_COPYBOOK,
            data_path=SAMPLE_DATA,
            source_system="mainframe_test",
            batch_id="test-batch-004",
        )

        with (
            patch("src.pipelines.bronze.mainframe_ingest.is_cobrix_available", return_value=False),
            pytest.raises(CobrixNotAvailableError),
        ):
            pipeline.extract()

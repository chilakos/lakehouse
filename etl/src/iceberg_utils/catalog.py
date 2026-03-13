"""Nessie catalog interaction utilities for Iceberg tables.

Provides functions for:
- Creating SparkSession configured with Iceberg REST catalog (Nessie)
- Creating namespaces and Iceberg tables
- Writing data to and reading from Iceberg tables
- S3/MinIO path-style-access configuration

IMPORTANT: Uses REST catalog type (not Nessie-specific type) per anti-pattern guidance.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession
    from pyspark.sql.types import StructType


def get_spark_session(
    nessie_uri: str | None = None,
    warehouse: str | None = None,
    s3_endpoint: str | None = None,
    app_name: str = "lakehouse-etl",
) -> SparkSession:
    """Create a SparkSession configured for Iceberg with Nessie REST catalog.

    Uses REST catalog type for better forward compatibility (not Nessie-specific).
    If s3_endpoint is provided, configures S3 for MinIO (path-style-access, endpoint override).

    Args:
        nessie_uri: Nessie REST API base URL. Defaults to NESSIE_URI env var or localhost.
        warehouse: Iceberg warehouse name. Defaults to NESSIE_WAREHOUSE env var or "lakehouse".
        s3_endpoint: S3-compatible endpoint URL (for MinIO). None for AWS S3.
        app_name: Spark application name.

    Returns:
        Configured SparkSession with Iceberg REST catalog named "lakehouse".
    """
    if nessie_uri is None:
        nessie_uri = os.environ.get("NESSIE_URI", "http://localhost:19120")
    if warehouse is None:
        warehouse = os.environ.get("NESSIE_WAREHOUSE", "lakehouse")

    builder = (
        SparkSession.builder.appName(app_name)
        .config(
            "spark.jars.packages",
            "org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1",
        )
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config("spark.sql.catalog.lakehouse", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.lakehouse.type", "rest")
        .config("spark.sql.catalog.lakehouse.uri", f"{nessie_uri}/iceberg")
        .config("spark.sql.catalog.lakehouse.warehouse", warehouse)
        .config(
            "spark.sql.catalog.lakehouse.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO",
        )
        .config("spark.sql.defaultCatalog", "lakehouse")
    )

    if s3_endpoint:
        access_key = os.environ.get("MINIO_ACCESS_KEY", "admin")
        secret_key = os.environ.get("MINIO_SECRET_KEY", "admin123456")
        builder = (
            builder.config("spark.sql.catalog.lakehouse.s3.endpoint", s3_endpoint)
            .config("spark.sql.catalog.lakehouse.s3.access-key-id", access_key)
            .config("spark.sql.catalog.lakehouse.s3.secret-access-key", secret_key)
            .config("spark.sql.catalog.lakehouse.s3.path-style-access", "true")
        )

    return builder.master("local[*]").getOrCreate()


def create_namespace(spark: SparkSession, namespace: str) -> None:
    """Create an Iceberg namespace if it does not already exist.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Namespace name to create.
    """
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS lakehouse.{namespace}")


def create_iceberg_table(
    spark: SparkSession,
    namespace: str,
    table_name: str,
    schema: StructType,
    location: str,
    partition_by: list[str] | None = None,
) -> None:
    """Create an Iceberg table with the specified schema and location.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Target namespace.
        table_name: Table name to create.
        schema: PySpark StructType defining the table schema.
        location: S3/MinIO location URI (e.g., s3://lakehouse-data/warehouse/trades).
        partition_by: Optional list of partition column expressions
                      (e.g., ["days(trade_date)"] or ["symbol"]).
    """
    full_table_name = f"lakehouse.{namespace}.{table_name}"

    # Create empty DataFrame with the schema to derive column definitions
    empty_df = spark.createDataFrame([], schema)
    empty_df.createOrReplaceTempView("_temp_schema_view")

    # Build CREATE TABLE statement
    columns = ", ".join(
        f"{field.name} {_spark_type_to_sql(field.dataType)}" for field in schema.fields
    )

    partition_clause = ""
    if partition_by:
        partition_clause = f" PARTITIONED BY ({', '.join(partition_by)})"

    create_sql = (
        f"CREATE TABLE IF NOT EXISTS {full_table_name} "
        f"({columns}) "
        f"USING iceberg "
        f"LOCATION '{location}'"
        f"{partition_clause}"
    )

    spark.sql(create_sql)


def write_data(
    spark: SparkSession,
    namespace: str,
    table_name: str,
    data: list[dict],
    schema: StructType,
) -> None:
    """Write data to an Iceberg table in append mode.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Target namespace.
        table_name: Target table name.
        data: List of dictionaries to write.
        schema: PySpark StructType for the DataFrame.
    """
    full_table_name = f"lakehouse.{namespace}.{table_name}"
    df = spark.createDataFrame(data, schema)
    df.writeTo(full_table_name).append()


def read_table(
    spark: SparkSession,
    namespace: str,
    table_name: str,
) -> DataFrame:
    """Read an Iceberg table and return as DataFrame.

    Args:
        spark: Active SparkSession with Iceberg catalog configured.
        namespace: Source namespace.
        table_name: Source table name.

    Returns:
        PySpark DataFrame with the table contents.
    """
    full_table_name = f"lakehouse.{namespace}.{table_name}"
    return spark.table(full_table_name)


def _spark_type_to_sql(data_type) -> str:
    """Convert a PySpark DataType to SQL type string for CREATE TABLE.

    Args:
        data_type: PySpark DataType instance.

    Returns:
        SQL type string representation.
    """
    from pyspark.sql.types import (
        BooleanType,
        DateType,
        DecimalType,
        DoubleType,
        FloatType,
        IntegerType,
        LongType,
        StringType,
        TimestampType,
    )

    type_map = {
        StringType: "STRING",
        IntegerType: "INT",
        LongType: "BIGINT",
        FloatType: "FLOAT",
        DoubleType: "DOUBLE",
        BooleanType: "BOOLEAN",
        DateType: "DATE",
        TimestampType: "TIMESTAMP",
    }

    for spark_type, sql_type in type_map.items():
        if isinstance(data_type, spark_type):
            return sql_type

    if isinstance(data_type, DecimalType):
        return f"DECIMAL({data_type.precision}, {data_type.scale})"

    # Fallback
    return str(data_type).upper()

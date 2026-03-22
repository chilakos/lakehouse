"""Trino query utilities for reading, writing, and validating Iceberg tables.

Provides functions for:
- Creating Trino DBAPI connections with workload-tagged sources
- Executing queries and DDL statements
- Retrieving table schema and row counts
- Connection management with cursor lifecycle

Uses the trino Python package (trino.dbapi) for DBAPI 2.0 compliant access.

Workload isolation: every connection specifies a `source` string that Trino's
resource-groups engine uses to route the query to the correct memory/concurrency
bucket. Use the named constructors (get_etl_connection, get_soda_connection, etc.)
rather than get_trino_connection directly — they set the correct source tag.

Resource group routing (rules.json):
  svc_etl_pipeline / svc_airflow  → engineering.etl_pipelines  (40% memory, 15 concurrent)
  svc_soda                         → engineering.soda_quality   (15% memory,  5 concurrent)
  source=cube                      → bi.cube_semantic           (20% memory, 20 concurrent)
  source=PowerBI                   → bi.power_bi                (10% memory, 15 concurrent)
  svc_borealis / svc_fastapi_ai    → ai_agents                  ( 5% memory,  5 concurrent)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trino.dbapi import Connection


def get_trino_connection(
    host: str | None = None,
    port: int | None = None,
    user: str = "trino",
    catalog: str = "iceberg",
    schema: str = "default",
    source: str = "python-client",
) -> Connection:
    """Create a Trino DBAPI connection.

    Prefer the named constructors below (get_etl_connection, get_soda_connection,
    etc.) which set the correct `source` tag for resource-group routing.

    Args:
        host: Trino coordinator hostname. Defaults to TRINO_HOST env or localhost.
        port: Trino coordinator port. Defaults to TRINO_PORT env or 8080.
        user: Trino user / service account name. Logged by Ranger for every query.
        catalog: Default Trino catalog to use.
        schema: Default schema within the catalog.
        source: Workload tag used by resource-groups rules.json to route this
            connection to the correct memory/concurrency bucket.

    Returns:
        Trino DBAPI Connection object.
    """
    import trino

    if host is None:
        host = os.environ.get("TRINO_HOST", "localhost")
    if port is None:
        port = int(os.environ.get("TRINO_PORT", "8080"))

    return trino.dbapi.connect(
        host=host,
        port=port,
        user=user,
        catalog=catalog,
        schema=schema,
        source=source,
    )


def get_etl_connection(schema: str = "default") -> Connection:
    """Connection for Airflow DAGs and Python ETL pipelines.

    Routes to: engineering.etl_pipelines (40% memory, 15 concurrent, 4h timeout).
    """
    return get_trino_connection(
        user=os.environ.get("TRINO_ETL_USER", "svc_etl_pipeline"),
        schema=schema,
        source="airflow-etl-pipeline",
    )


def get_soda_connection(schema: str = "default") -> Connection:
    """Connection for Soda quality gate checks.

    Routes to: engineering.soda_quality (15% memory, 5 concurrent, 30m timeout).
    """
    return get_trino_connection(
        user=os.environ.get("TRINO_SODA_USER", "svc_soda"),
        schema=schema,
        source="soda-quality-gate",
    )


def get_schema_ops_connection(schema: str = "default") -> Connection:
    """Connection for DDL operations — CREATE TABLE, ALTER TABLE, etc.

    Routes to: engineering.schema_ops (5% memory, 3 concurrent, 10m timeout).
    """
    return get_trino_connection(
        user=os.environ.get("TRINO_ETL_USER", "svc_etl_pipeline"),
        schema=schema,
        source="schema-migration",
    )


def get_ai_connection(schema: str = "gold") -> Connection:
    """Connection for AI agent queries (FastAPI middleware, Borealis, RBC Assist).

    Routes to: ai_agents (5% memory, 5 concurrent, 2m timeout).
    """
    return get_trino_connection(
        user=os.environ.get("TRINO_AI_USER", "svc_fastapi_ai"),
        schema=schema,
        source="fastapi-ai-middleware",
    )


def get_nessie_branch_connection(
    branch: str,
    schema: str = "default",
    source: str = "soda-quality-gate",
) -> Connection:
    """Connection pointing at a specific Nessie branch.

    Used by Soda quality gates to validate staged data on an ingest branch
    before the Nessie merge to main.

    Args:
        branch: Nessie branch name (e.g. "ingest/account-master-20260320").
        schema: Default schema.
        source: Workload source tag for resource-group routing.
    """
    import trino

    host = os.environ.get("TRINO_HOST", "localhost")
    port = int(os.environ.get("TRINO_PORT", "8080"))
    user = os.environ.get("TRINO_SODA_USER", "svc_soda")

    return trino.dbapi.connect(
        host=host,
        port=port,
        user=user,
        catalog="iceberg",
        schema=schema,
        source=source,
        session_properties={"iceberg.nessie_ref": branch},
    )


def execute_query(conn: Connection, sql: str) -> list[tuple]:
    """Execute a SQL query and return all result rows."""
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        cursor.close()


def execute_ddl(conn: Connection, sql: str) -> None:
    """Execute a DDL statement. Calls fetchall() to force completion."""
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        cursor.fetchall()
    finally:
        cursor.close()


def get_table_schema(conn: Connection, schema: str, table: str) -> list[dict]:
    """Get column names and types from a table using DESCRIBE."""
    rows = execute_query(conn, f"DESCRIBE {schema}.{table}")
    return [{"name": row[0], "type": row[1]} for row in rows]


def get_table_schema_fields(conn: Connection, schema: str, table: str) -> list[str]:
    """Get column names only — used by the tag classifier."""
    rows = execute_query(
        conn,
        f"""
        SELECT column_name
        FROM   iceberg.information_schema.columns
        WHERE  table_schema = '{schema}'
        AND    table_name   = '{table}'
        ORDER  BY ordinal_position
        """,
    )
    return [row[0] for row in rows]


def get_table_row_count(conn: Connection, schema: str, table: str) -> int:
    """Get the row count of a table."""
    rows = execute_query(conn, f"SELECT COUNT(*) FROM {schema}.{table}")
    return rows[0][0]

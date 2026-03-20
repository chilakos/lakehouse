"""Trino query utilities for reading, writing, and validating Iceberg tables.

Provides functions for:
- Creating Trino DBAPI connections
- Executing queries and DDL statements
- Retrieving table schema and row counts
- Connection management with cursor lifecycle

Uses the trino Python package (trino.dbapi) for DBAPI 2.0 compliant access.
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
) -> Connection:
    """Create a Trino DBAPI connection.

    Args:
        host: Trino coordinator hostname. Defaults to TRINO_HOST env or localhost.
        port: Trino coordinator port. Defaults to TRINO_PORT env or 8080.
        user: Trino user name for the connection.
        catalog: Default Trino catalog to use.
        schema: Default schema within the catalog.

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
    )


def execute_query(conn: Connection, sql: str) -> list[tuple]:
    """Execute a SQL query and return all result rows.

    Handles cursor creation and cleanup automatically.

    Args:
        conn: Active Trino DBAPI connection.
        sql: SQL query string to execute.

    Returns:
        List of tuples containing the result rows.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        cursor.close()


def execute_ddl(conn: Connection, sql: str) -> None:
    """Execute a DDL statement (CREATE, ALTER, DROP, INSERT, UPDATE, DELETE, MERGE).

    Handles cursor creation and cleanup automatically.

    Args:
        conn: Active Trino DBAPI connection.
        sql: DDL/DML statement to execute.
    """
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        # Consume any results to ensure statement completes
        cursor.fetchall()
    finally:
        cursor.close()


def get_table_schema(conn: Connection, schema: str, table: str) -> list[dict]:
    """Get column names and types from a table using DESCRIBE.

    Args:
        conn: Active Trino DBAPI connection.
        schema: Schema (namespace) containing the table.
        table: Table name.

    Returns:
        List of dicts with 'name' and 'type' keys for each column.
    """
    rows = execute_query(conn, f"DESCRIBE {schema}.{table}")
    return [{"name": row[0], "type": row[1]} for row in rows]


def get_table_row_count(conn: Connection, schema: str, table: str) -> int:
    """Get the row count of a table.

    Args:
        conn: Active Trino DBAPI connection.
        schema: Schema (namespace) containing the table.
        table: Table name.

    Returns:
        Integer row count.
    """
    rows = execute_query(conn, f"SELECT COUNT(*) FROM {schema}.{table}")
    return rows[0][0]

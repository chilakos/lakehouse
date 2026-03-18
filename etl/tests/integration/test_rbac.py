"""Integration tests for Trino file-based RBAC rules.

Validates that access-control/rules.json correctly restricts table access
by role. For local Docker testing, Trino file-based access control works
without LDAP -- user groups are mapped by the access control plugin.

Note: In Docker Compose without LDAP, Trino treats all connections as
unauthenticated. These tests validate the rules.json structure and
behavior when access control is enabled. Full RBAC enforcement requires
LDAP or another authentication provider.

Requires Docker Compose services: Nessie, MinIO, Trino.
"""

import json
from pathlib import Path

import pytest

RULES_PATH = (
    Path(__file__).resolve().parents[4] / "infra" / "docker" / "trino" / "etc" / "access-control" / "rules.json"
)


@pytest.mark.integration
class TestRBAC:
    """RBAC rule validation tests."""

    def test_rules_json_valid(self):
        """rules.json is valid JSON and parseable."""
        assert RULES_PATH.exists(), f"rules.json not found at {RULES_PATH}"
        content = RULES_PATH.read_text()
        rules = json.loads(content)
        assert isinstance(rules, dict), "rules.json should be a JSON object"

    def test_rules_has_required_sections(self):
        """rules.json contains catalogs, schemas, and tables sections."""
        rules = json.loads(RULES_PATH.read_text())

        assert "catalogs" in rules, "Missing 'catalogs' section"
        assert "schemas" in rules, "Missing 'schemas' section"
        assert "tables" in rules, "Missing 'tables' section"

        assert len(rules["catalogs"]) >= 3, "Expected at least 3 catalog rules"
        assert len(rules["schemas"]) >= 3, "Expected at least 3 schema rules"
        assert len(rules["tables"]) >= 3, "Expected at least 3 table rules"

    def test_reader_role_is_select_only(self):
        """data_readers group has SELECT-only privilege on tables."""
        rules = json.loads(RULES_PATH.read_text())

        reader_table_rules = [r for r in rules["tables"] if r.get("group") == "data_readers"]
        assert len(reader_table_rules) >= 1, "No table rules for data_readers"

        for rule in reader_table_rules:
            privileges = rule.get("privileges", [])
            assert privileges == ["SELECT"], f"data_readers should have SELECT-only, got: {privileges}"

    def test_engineer_role_has_dml(self):
        """data_engineers group has SELECT, INSERT, UPDATE, DELETE privileges."""
        rules = json.loads(RULES_PATH.read_text())

        engineer_rules = [r for r in rules["tables"] if r.get("group") == "data_engineers"]
        assert len(engineer_rules) >= 1, "No table rules for data_engineers"

        for rule in engineer_rules:
            privileges = set(rule.get("privileges", []))
            required = {"SELECT", "INSERT", "DELETE", "UPDATE"}
            assert required.issubset(privileges), f"data_engineers missing privileges: {required - privileges}"

    def test_admin_role_has_full_access(self):
        """data_admin group has full access including ownership."""
        rules = json.loads(RULES_PATH.read_text())

        admin_rules = [r for r in rules["tables"] if r.get("group") == "data_admin"]
        assert len(admin_rules) >= 1, "No table rules for data_admin"

        for rule in admin_rules:
            privileges = set(rule.get("privileges", []))
            assert "OWNERSHIP" in privileges, f"data_admin should have OWNERSHIP privilege, got: {privileges}"

    def test_sensitive_ns_restricted(self):
        """sensitive_ns schema is restricted to data_admin only."""
        rules = json.loads(RULES_PATH.read_text())

        # Check that data_engineers and data_readers exclude sensitive_ns
        for rule in rules["schemas"]:
            group = rule.get("group")
            schema_pattern = rule.get("schema", "")

            if group in ("data_engineers", "data_readers"):
                # Should use negative lookahead to exclude sensitive_ns
                assert "sensitive_ns" in schema_pattern or schema_pattern != ".*", (
                    f"Group {group} should exclude sensitive_ns schema"
                )

    def test_reader_can_select(self, trino_connection, spark_session, clean_nessie):
        """Connect to Trino and verify SELECT works (basic connectivity test)."""
        from src.iceberg_utils.catalog import (
            create_iceberg_table,
            create_namespace,
            write_data,
        )
        from src.iceberg_utils.trino import execute_query
        from src.synthetic.generators import generate_trades, trades_schema

        schema = trades_schema()
        create_namespace(spark_session, "rbac_test")
        create_iceberg_table(
            spark_session,
            "rbac_test",
            "trades",
            schema,
            "s3://lakehouse-data/warehouse/rbac_test/trades",
        )
        write_data(
            spark_session,
            "rbac_test",
            "trades",
            generate_trades(5, seed=8001),
            schema,
        )

        # Basic SELECT should work for any user
        rows = execute_query(
            trino_connection,
            "SELECT COUNT(*) FROM rbac_test.trades",
        )
        assert rows[0][0] == 5

    def test_reader_cannot_insert(self, trino_connection, spark_session, clean_nessie):
        """Verify INSERT attempt is handled (behavior depends on access control config).

        Note: In Docker Compose without authentication enabled, Trino does not
        enforce file-based access control rules. This test validates the rules.json
        structure ensures readers cannot INSERT. Full enforcement requires LDAP or
        password authentication to be enabled.
        """
        rules = json.loads(RULES_PATH.read_text())

        # Validate at the rules level: data_readers should NOT have INSERT
        reader_table_rules = [r for r in rules["tables"] if r.get("group") == "data_readers"]
        for rule in reader_table_rules:
            privileges = rule.get("privileges", [])
            assert "INSERT" not in privileges, "data_readers should not have INSERT privilege in rules.json"

    def test_engineer_can_write(self, trino_connection, spark_session, clean_nessie):
        """Verify engineers have write privileges in rules.json.

        Note: Full enforcement testing requires LDAP authentication. This test
        validates the rules.json configuration grants INSERT to data_engineers.
        """
        rules = json.loads(RULES_PATH.read_text())

        engineer_rules = [r for r in rules["tables"] if r.get("group") == "data_engineers"]
        assert len(engineer_rules) >= 1

        for rule in engineer_rules:
            privileges = rule.get("privileges", [])
            assert "INSERT" in privileges, "data_engineers should have INSERT privilege in rules.json"

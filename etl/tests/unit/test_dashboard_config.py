"""Unit tests for Grafana dashboard configuration.

Validates that pipeline_observability.json:
- Is valid JSON
- Has required panel types (stat, timeseries, table)
- References the Prometheus datasource
- Contains expected Airflow metric queries

@pytest.mark.unit
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DASHBOARDS_DIR = Path(__file__).resolve().parents[3] / "infra" / "docker" / "grafana" / "dashboards"
DASHBOARD_PATH = DASHBOARDS_DIR / "pipeline_observability.json"

PROVISIONING_DIR = Path(__file__).resolve().parents[3] / "infra" / "docker" / "grafana" / "provisioning"
DATASOURCES_PATH = PROVISIONING_DIR / "datasources.yml"
DASHBOARDS_PROV_PATH = PROVISIONING_DIR / "dashboards.yml"


@pytest.mark.unit
class TestDashboardConfig:
    """Tests for Grafana dashboard JSON structure and content."""

    def _load_dashboard(self) -> dict:
        """Load and parse the dashboard JSON."""
        return json.loads(DASHBOARD_PATH.read_text())

    def test_dashboard_file_exists(self):
        """pipeline_observability.json must exist."""
        assert DASHBOARD_PATH.exists(), f"Dashboard file not found at {DASHBOARD_PATH}"

    def test_dashboard_is_valid_json(self):
        """Dashboard file must parse as valid JSON."""
        try:
            self._load_dashboard()
        except json.JSONDecodeError as e:
            pytest.fail(f"Dashboard file is not valid JSON: {e}")

    def test_dashboard_has_title(self):
        """Dashboard must have a title."""
        dashboard = self._load_dashboard()
        assert "title" in dashboard
        assert dashboard["title"] == "Pipeline Observability"

    def test_dashboard_has_panels(self):
        """Dashboard must have panels defined."""
        dashboard = self._load_dashboard()
        assert "panels" in dashboard
        assert len(dashboard["panels"]) > 0

    def test_dashboard_has_stat_panels(self):
        """Dashboard must include stat panel type for summary metrics."""
        dashboard = self._load_dashboard()
        panel_types = [p.get("type") for p in dashboard["panels"]]
        assert "stat" in panel_types, f"Expected 'stat' panel type for summary metrics, found: {set(panel_types)}"

    def test_dashboard_has_timeseries_panels(self):
        """Dashboard must include timeseries panel type for graphs."""
        dashboard = self._load_dashboard()
        panel_types = [p.get("type") for p in dashboard["panels"]]
        assert "timeseries" in panel_types, f"Expected 'timeseries' panel type for graphs, found: {set(panel_types)}"

    def test_dashboard_has_table_panels(self):
        """Dashboard must include table panel type for status overview."""
        dashboard = self._load_dashboard()
        panel_types = [p.get("type") for p in dashboard["panels"]]
        assert "table" in panel_types, f"Expected 'table' panel type for status overview, found: {set(panel_types)}"

    def test_datasource_references_prometheus(self):
        """All data panels must reference Prometheus datasource."""
        dashboard = self._load_dashboard()
        for panel in dashboard["panels"]:
            ds = panel.get("datasource", {})
            if ds and isinstance(ds, dict) and ds.get("type"):
                assert ds["type"] == "prometheus", (
                    f"Panel '{panel.get('title', 'unknown')}' uses datasource '{ds['type']}', expected 'prometheus'"
                )

    def test_queries_reference_airflow_metrics(self):
        """Panel queries must reference expected Airflow metric names."""
        dashboard = self._load_dashboard()

        all_queries = []
        for panel in dashboard["panels"]:
            targets = panel.get("targets", [])
            for target in targets:
                expr = target.get("expr", "")
                if expr:
                    all_queries.append(expr)

        queries_str = " ".join(all_queries)

        # Verify key Airflow metric patterns are referenced
        assert "airflow_dag_run" in queries_str, "Dashboard must query airflow_dag_run metrics"
        assert "airflow_executor" in queries_str or "airflow_dag_run" in queries_str, (
            "Dashboard must query Airflow operational metrics"
        )

    def test_dashboard_minimum_panel_count(self):
        """Dashboard must have at least 10 panels (summary + ops + data quality)."""
        dashboard = self._load_dashboard()
        # Exclude row-type panels from count
        data_panels = [p for p in dashboard["panels"] if p.get("type") != "row"]
        assert len(data_panels) >= 10, f"Expected at least 10 data panels, found {len(data_panels)}"

    def test_provisioning_datasources_exists(self):
        """Grafana datasources provisioning file must exist."""
        assert DATASOURCES_PATH.exists(), f"Datasources provisioning file not found at {DATASOURCES_PATH}"

    def test_provisioning_dashboards_exists(self):
        """Grafana dashboards provisioning file must exist."""
        assert DASHBOARDS_PROV_PATH.exists(), f"Dashboards provisioning file not found at {DASHBOARDS_PROV_PATH}"

    def test_datasources_references_prometheus(self):
        """Datasources config must reference Prometheus."""
        content = DATASOURCES_PATH.read_text()
        assert "prometheus" in content.lower(), "Datasources config must reference Prometheus"

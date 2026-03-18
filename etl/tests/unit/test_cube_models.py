"""Unit tests for Cube YAML metric definitions and Docker Compose services.

Validates that Cube semantic layer YAML files have correct structure,
measures, dimensions, and glossary links. Also validates Docker Compose
has cube-api and cubestore services properly configured.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# Resolve paths relative to the repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
CUBES_DIR = REPO_ROOT / "semantic" / "model" / "cubes"
VIEWS_DIR = REPO_ROOT / "semantic" / "model" / "views"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


def _load_yaml(path: Path) -> dict:
    """Load and parse a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


# --- Trading metrics cube tests ---


@pytest.mark.unit
class TestTradingMetricsYaml:
    """Tests for semantic/model/cubes/trading_metrics.yml."""

    @pytest.fixture(autouse=True)
    def load_trading_metrics(self):
        self.cube = _load_yaml(CUBES_DIR / "trading_metrics.yml")

    def test_trading_metrics_yaml_has_required_measures(self):
        """trading_metrics.yml contains total_notional, trade_count, avg_price measures with correct types."""
        cubes = self.cube["cubes"]
        trading = next(c for c in cubes if c["name"] == "trading_metrics")
        measures = {m["name"]: m for m in trading["measures"]}

        assert "total_notional" in measures
        assert measures["total_notional"]["type"] == "sum"

        assert "trade_count" in measures
        assert measures["trade_count"]["type"] == "sum"

        assert "avg_price" in measures
        assert measures["avg_price"]["type"] == "avg"

    def test_trading_metrics_yaml_has_dimensions(self):
        """trading_metrics.yml has symbol and side dimensions."""
        cubes = self.cube["cubes"]
        trading = next(c for c in cubes if c["name"] == "trading_metrics")
        dims = {d["name"] for d in trading["dimensions"]}

        assert "symbol" in dims
        assert "side" in dims

    def test_trading_metrics_yaml_has_glossary_links(self):
        """measures have meta.glossary_term fields."""
        cubes = self.cube["cubes"]
        trading = next(c for c in cubes if c["name"] == "trading_metrics")

        for measure in trading["measures"]:
            assert "meta" in measure, f"Measure {measure['name']} missing meta"
            assert "glossary_term" in measure["meta"], f"Measure {measure['name']} missing meta.glossary_term"


# --- Risk exposure cube tests ---


@pytest.mark.unit
class TestRiskExposureYaml:
    """Tests for semantic/model/cubes/risk_exposure.yml."""

    @pytest.fixture(autouse=True)
    def load_risk_exposure(self):
        self.cube = _load_yaml(CUBES_DIR / "risk_exposure.yml")

    def test_risk_exposure_yaml_has_required_measures(self):
        """risk_exposure.yml contains required measures.

        Checks total_market_value, total_var_95, total_var_99,
        total_expected_shortfall, position_count.
        """
        cubes = self.cube["cubes"]
        risk = next(c for c in cubes if c["name"] == "risk_exposure")
        measures = {m["name"]: m for m in risk["measures"]}

        assert "total_market_value" in measures
        assert "total_var_95" in measures
        assert "total_var_99" in measures
        assert "total_expected_shortfall" in measures
        assert "position_count" in measures

    def test_risk_exposure_yaml_has_dimensions(self):
        """risk_exposure.yml has account_id, sector, currency dimensions."""
        cubes = self.cube["cubes"]
        risk = next(c for c in cubes if c["name"] == "risk_exposure")
        dims = {d["name"] for d in risk["dimensions"]}

        assert "account_id" in dims
        assert "sector" in dims
        assert "currency" in dims


# --- View tests ---


@pytest.mark.unit
class TestTradingViewYaml:
    """Tests for semantic/model/views/trading_view.yml."""

    @pytest.fixture(autouse=True)
    def load_trading_view(self):
        self.view = _load_yaml(VIEWS_DIR / "trading_view.yml")

    def test_trading_view_yaml_includes_all_measures(self):
        """trading_view.yml references all trading_metrics measures."""
        views = self.view["views"]
        trading_view = next(v for v in views if v["name"] == "trading_dashboard")

        # Collect all included measure names
        included = set()
        for include in trading_view.get("includes", []):
            if "members" in include:
                for member in include["members"]:
                    included.add(member)

        # Must include all three trading measures
        expected = {"trading_metrics.total_notional", "trading_metrics.trade_count", "trading_metrics.avg_price"}
        assert expected.issubset(included), f"Missing measures: {expected - included}"


@pytest.mark.unit
class TestRiskExposureViewYaml:
    """Tests for semantic/model/views/risk_exposure_view.yml."""

    @pytest.fixture(autouse=True)
    def load_risk_view(self):
        self.view = _load_yaml(VIEWS_DIR / "risk_exposure_view.yml")

    def test_risk_exposure_view_yaml_includes_all_measures(self):
        """risk_exposure_view.yml references all risk_exposure measures."""
        views = self.view["views"]
        risk_view = next(v for v in views if v["name"] == "risk_dashboard")

        included = set()
        for include in risk_view.get("includes", []):
            if "members" in include:
                for member in include["members"]:
                    included.add(member)

        expected = {
            "risk_exposure.total_market_value",
            "risk_exposure.total_var_95",
            "risk_exposure.total_var_99",
            "risk_exposure.total_expected_shortfall",
            "risk_exposure.position_count",
        }
        assert expected.issubset(included), f"Missing measures: {expected - included}"


# --- Cross-YAML tests ---


@pytest.mark.unit
class TestCubeYamlNoDuplicates:
    """Cross-file validation."""

    def test_cube_yaml_no_duplicate_measure_names(self):
        """across all YAML files, no two measures share a name."""
        all_measures: list[str] = []

        for yml_file in CUBES_DIR.glob("*.yml"):
            data = _load_yaml(yml_file)
            for cube in data.get("cubes", []):
                for measure in cube.get("measures", []):
                    all_measures.append(measure["name"])

        assert len(all_measures) == len(set(all_measures)), (
            f"Duplicate measures found: {[m for m in all_measures if all_measures.count(m) > 1]}"
        )


# --- Docker Compose tests ---


@pytest.mark.unit
class TestCubeDockerServices:
    """Tests for Cube services in docker-compose.yml."""

    @pytest.fixture(autouse=True)
    def load_compose(self):
        self.compose = _load_yaml(COMPOSE_FILE)

    def test_cube_docker_services_in_compose(self):
        """docker-compose.yml has cube-api and cubestore services."""
        services = self.compose["services"]
        assert "cube-api" in services, "cube-api service not found in docker-compose.yml"
        assert "cubestore" in services, "cubestore service not found in docker-compose.yml"

    def test_cube_api_connects_to_trino(self):
        """cube-api has CUBEJS_DB_TYPE=trino, CUBEJS_DB_HOST=trino."""
        cube_api = self.compose["services"]["cube-api"]
        env = cube_api["environment"]
        assert env.get("CUBEJS_DB_TYPE") == "trino"
        assert env.get("CUBEJS_DB_HOST") == "trino"

    def test_cube_sql_api_port(self):
        """cube-api exposes 15432 for SQL API."""
        cube_api = self.compose["services"]["cube-api"]
        ports = cube_api["ports"]
        port_strs = [str(p) for p in ports]
        assert any("15432" in p for p in port_strs), f"Port 15432 not found in cube-api ports: {port_strs}"

    def test_cube_model_volumes_mounted(self):
        """cube-api mounts semantic/model as /cube/conf/model."""
        cube_api = self.compose["services"]["cube-api"]
        volumes = cube_api.get("volumes", [])
        vol_strs = [str(v) for v in volumes]
        assert any("/cube/conf/model" in v for v in vol_strs), (
            f"semantic/model not mounted to /cube/conf/model in cube-api volumes: {vol_strs}"
        )

    def test_cubestore_data_volume(self):
        """cubestore has cubestore-data volume."""
        # Check that the cubestore-data volume is defined
        volumes = self.compose.get("volumes", {})
        assert "cubestore-data" in volumes, "cubestore-data volume not defined"

        # Check cubestore service uses it
        cubestore = self.compose["services"]["cubestore"]
        svc_volumes = cubestore.get("volumes", [])
        vol_strs = [str(v) for v in svc_volumes]
        assert any("cubestore-data" in v for v in vol_strs), (
            f"cubestore-data not mounted in cubestore volumes: {vol_strs}"
        )

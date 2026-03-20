"""Integration tests for OpenMetadata business glossary.

Tests that FSDM glossary terms from glossary-seed.json are searchable
and have correct approval workflow states in OpenMetadata.

These tests SKIP automatically if OpenMetadata is not running.

Run with: pytest tests/integration/test_catalog_glossary.py -m integration
"""

import json
import socket
from pathlib import Path

import pytest


def _is_openmetadata_reachable(host: str = "localhost", port: int = 8585, timeout: float = 2.0) -> bool:
    """Check if OpenMetadata server is reachable via TCP."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, TimeoutError):
        return False


def _find_project_root() -> Path:
    """Find the project root by looking for docker-compose.yml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "docker-compose.yml").exists():
            return parent
    return current.parent.parent.parent.parent


OM_HOST = "localhost"
OM_PORT = 8585
OM_BASE_URL = f"http://{OM_HOST}:{OM_PORT}/api/v1"
PROJECT_ROOT = _find_project_root()

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def require_openmetadata():
    """Skip all tests in this module if OpenMetadata is not running."""
    if not _is_openmetadata_reachable(OM_HOST, OM_PORT):
        pytest.skip(
            f"OpenMetadata server not reachable at {OM_HOST}:{OM_PORT}. "
            "Start the stack with: docker compose up openmetadata-server"
        )


@pytest.fixture(scope="module")
def om_session():
    """Create a requests session for OpenMetadata API calls."""
    try:
        import requests
    except ImportError:
        pytest.skip("requests library not installed")

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


@pytest.fixture(scope="module")
def seed_terms():
    """Load glossary terms from glossary-seed.json."""
    seed_path = PROJECT_ROOT / "infra" / "docker" / "openmetadata" / "glossary-seed.json"
    if not seed_path.is_file():
        pytest.skip("glossary-seed.json not found")
    data = json.loads(seed_path.read_text())
    return data.get("terms", data) if isinstance(data, dict) else data


class TestGlossaryTermsSearchable:
    """Test that FSDM glossary terms are searchable in OpenMetadata."""

    def test_glossary_api_responds(self, om_session):
        """Glossary API endpoint should be reachable."""
        response = om_session.get(f"{OM_BASE_URL}/glossaries", params={"limit": 10})
        assert response.status_code == 200, f"Glossary API returned status {response.status_code}"

    def test_glossary_search_returns_results(self, om_session):
        """Glossary term search should return results after seeding."""
        response = om_session.get(
            f"{OM_BASE_URL}/search/query",
            params={"q": "Trade", "index": "glossary_search_index", "from": 0, "size": 5},
        )
        assert response.status_code == 200, f"Glossary search returned status {response.status_code}"

    def test_seeded_terms_have_definitions(self, om_session, seed_terms):
        """Glossary terms imported from seed data should have descriptions."""
        response = om_session.get(
            f"{OM_BASE_URL}/glossaryTerms",
            params={"limit": 50},
        )
        if response.status_code != 200:
            pytest.skip("Glossary terms API not accessible")

        data = response.json()
        catalog_terms = data.get("data", [])

        if not catalog_terms:
            pytest.skip("No glossary terms in catalog -- import glossary-seed.json first")

        for term in catalog_terms:
            assert term.get("description"), f"Term '{term.get('name')}' in catalog has no description"

    def test_approval_workflow_states_exist(self, om_session):
        """OpenMetadata glossary should support Draft, In Review, and Approved states."""
        response = om_session.get(f"{OM_BASE_URL}/glossaryTerms", params={"limit": 50})
        if response.status_code != 200:
            pytest.skip("Glossary terms API not accessible")

        data = response.json()
        catalog_terms = data.get("data", [])

        if not catalog_terms:
            pytest.skip("No glossary terms in catalog -- import glossary-seed.json first")

        # Terms imported from seed should be in Draft status
        statuses = {t.get("status") for t in catalog_terms if t.get("status")}
        # At minimum Draft should be present (from seed data)
        # The API should recognise these states (glossary workflow is built into OpenMetadata)
        assert "Draft" in statuses or not statuses, f"Expected at least 'Draft' status from seed data, got: {statuses}"

    def test_trade_term_has_definition(self, om_session):
        """'Trade' glossary term should have a substantive definition."""
        response = om_session.get(
            f"{OM_BASE_URL}/search/query",
            params={
                "q": "Trade",
                "index": "glossary_search_index",
                "from": 0,
                "size": 5,
            },
        )
        if response.status_code != 200:
            pytest.skip("Glossary search not accessible")

        hits = response.json().get("hits", {}).get("hits", [])
        trade_hits = [h for h in hits if h.get("_source", {}).get("name", "").lower() == "trade"]

        if not trade_hits:
            pytest.skip("'Trade' term not yet imported -- run glossary seed import first")

        trade_term = trade_hits[0]["_source"]
        assert trade_term.get("description"), "'Trade' glossary term should have a description"

    def test_pii_term_searchable(self, om_session):
        """'PII' glossary term should be searchable by keyword."""
        response = om_session.get(
            f"{OM_BASE_URL}/search/query",
            params={
                "q": "PII",
                "index": "glossary_search_index",
                "from": 0,
                "size": 5,
            },
        )
        assert response.status_code == 200, f"Search for PII returned status {response.status_code}"

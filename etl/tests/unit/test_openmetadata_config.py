"""Unit tests validating OpenMetadata infrastructure configuration files.

Tests that docker-compose.yml has the correct OpenMetadata services,
Trino ingestion YAML targets correct schemas, glossary seed data has
required FSDM terms, and memory limits are set correctly.

No external services required -- runs on file system inspection only.
"""

import json
from pathlib import Path

import pytest
import yaml


def _find_project_root() -> Path:
    """Find the project root by looking for .git directory or etl/pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
        if (parent / "etl" / "pyproject.toml").exists():
            return parent
    return current.parent.parent.parent.parent


PROJECT_ROOT = _find_project_root()


@pytest.mark.unit
class TestDockerComposeOpenMetadataServices:
    """Test that OpenMetadata services are correctly defined in docker-compose.yml."""

    @pytest.fixture(scope="class")
    def compose_data(self):
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        assert compose_path.is_file(), "docker-compose.yml not found"
        return yaml.safe_load(compose_path.read_text())

    def test_om_db_service_exists(self, compose_data):
        assert "om-db" in compose_data["services"], "om-db service not found in docker-compose.yml"

    def test_elasticsearch_service_exists(self, compose_data):
        assert "elasticsearch" in compose_data["services"], (
            "elasticsearch service not found in docker-compose.yml"
        )

    def test_openmetadata_server_service_exists(self, compose_data):
        assert "openmetadata-server" in compose_data["services"], (
            "openmetadata-server service not found in docker-compose.yml"
        )

    def test_openmetadata_ingestion_service_exists(self, compose_data):
        assert "openmetadata-ingestion" in compose_data["services"], (
            "openmetadata-ingestion service not found in docker-compose.yml"
        )

    def test_om_db_uses_postgres15(self, compose_data):
        om_db = compose_data["services"]["om-db"]
        assert om_db["image"].startswith("postgres:15"), "om-db should use postgres:15"

    def test_om_db_port_5436(self, compose_data):
        om_db = compose_data["services"]["om-db"]
        ports = om_db.get("ports", [])
        assert any("5436" in str(p) for p in ports), "om-db should be on host port 5436"

    def test_openmetadata_server_port_8585(self, compose_data):
        server = compose_data["services"]["openmetadata-server"]
        ports = server.get("ports", [])
        assert any("8585" in str(p) for p in ports), (
            "openmetadata-server should expose port 8585"
        )

    def test_openmetadata_ingestion_port_8086(self, compose_data):
        ingestion = compose_data["services"]["openmetadata-ingestion"]
        ports = ingestion.get("ports", [])
        assert any("8086" in str(p) for p in ports), (
            "openmetadata-ingestion should expose port 8086 (not 8080/8081 to avoid conflicts)"
        )

    def test_openmetadata_server_memory_limit(self, compose_data):
        server = compose_data["services"]["openmetadata-server"]
        mem = server.get("mem_limit", "")
        assert mem == "6g", f"openmetadata-server mem_limit should be '6g', got '{mem}'"

    def test_openmetadata_ingestion_memory_limit(self, compose_data):
        ingestion = compose_data["services"]["openmetadata-ingestion"]
        mem = ingestion.get("mem_limit", "")
        assert mem == "8g", f"openmetadata-ingestion mem_limit should be '8g', got '{mem}'"

    def test_openmetadata_server_depends_on_om_db(self, compose_data):
        server = compose_data["services"]["openmetadata-server"]
        depends = server.get("depends_on", {})
        if isinstance(depends, dict):
            assert "om-db" in depends, "openmetadata-server should depend on om-db"
        else:
            assert "om-db" in depends, "openmetadata-server should depend on om-db"

    def test_openmetadata_server_depends_on_elasticsearch(self, compose_data):
        server = compose_data["services"]["openmetadata-server"]
        depends = server.get("depends_on", {})
        if isinstance(depends, dict):
            assert "elasticsearch" in depends, (
                "openmetadata-server should depend on elasticsearch"
            )
        else:
            assert "elasticsearch" in depends, (
                "openmetadata-server should depend on elasticsearch"
            )

    def test_openmetadata_ingestion_depends_on_server(self, compose_data):
        ingestion = compose_data["services"]["openmetadata-ingestion"]
        depends = ingestion.get("depends_on", {})
        if isinstance(depends, dict):
            assert "openmetadata-server" in depends, (
                "openmetadata-ingestion should depend on openmetadata-server"
            )
        else:
            assert "openmetadata-server" in depends, (
                "openmetadata-ingestion should depend on openmetadata-server"
            )

    def test_openmetadata_server_has_db_env(self, compose_data):
        server = compose_data["services"]["openmetadata-server"]
        env = server.get("environment", {})
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = str(env)
        assert "DB_HOST" in env_str or "om-db" in env_str, (
            "openmetadata-server should have DB_HOST env var"
        )

    def test_openmetadata_server_has_elasticsearch_env(self, compose_data):
        server = compose_data["services"]["openmetadata-server"]
        env = server.get("environment", {})
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = str(env)
        assert "ELASTICSEARCH" in env_str or "elasticsearch" in env_str.lower(), (
            "openmetadata-server should have Elasticsearch env var"
        )

    def test_elasticsearch_single_node_mode(self, compose_data):
        es = compose_data["services"]["elasticsearch"]
        env = es.get("environment", {})
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = str(env)
        assert "single-node" in env_str, (
            "elasticsearch should run in single-node discovery mode"
        )

    def test_elasticsearch_security_disabled(self, compose_data):
        es = compose_data["services"]["elasticsearch"]
        env = es.get("environment", {})
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = str(env)
        assert "xpack.security.enabled=false" in env_str or "false" in env_str.lower(), (
            "elasticsearch xpack.security should be disabled for local dev"
        )

    def test_om_db_volume_defined(self, compose_data):
        volumes = compose_data.get("volumes", {})
        assert "om-db-data" in volumes, "om-db-data volume not defined"

    def test_es_data_volume_defined(self, compose_data):
        volumes = compose_data.get("volumes", {})
        assert "es-data" in volumes, "es-data volume not defined"

    def test_no_port_conflicts(self, compose_data):
        """Verify no port conflicts across all services."""
        used_ports = {}
        conflicting = []
        for svc_name, svc_config in compose_data["services"].items():
            for port_str in svc_config.get("ports", []):
                raw = str(port_str)
                host_port = raw.split(":")[0] if ":" in raw else raw
                host_port = host_port.split("/")[0].strip()
                if host_port in used_ports:
                    conflicting.append(
                        f"{svc_name}:{host_port} (already used by {used_ports[host_port]})"
                    )
                else:
                    used_ports[host_port] = svc_name
        assert not conflicting, f"Port conflicts detected: {conflicting}"

    def test_om_db_uses_postgres_driver(self, compose_data):
        """OpenMetadata server should use PostgreSQL (not MySQL)."""
        server = compose_data["services"]["openmetadata-server"]
        env = server.get("environment", {})
        if isinstance(env, list):
            env_str = " ".join(env)
        else:
            env_str = str(env)
        assert "postgresql" in env_str.lower() or "postgres" in env_str.lower(), (
            "openmetadata-server should use PostgreSQL driver (not MySQL)"
        )


@pytest.mark.unit
class TestTrinoIngestionConfig:
    """Test that Trino ingestion YAML is correctly configured for OpenMetadata."""

    @pytest.fixture(scope="class")
    def ingestion_config(self):
        config_path = (
            PROJECT_ROOT
            / "infra"
            / "docker"
            / "openmetadata"
            / "connectors"
            / "trino-ingestion.yaml"
        )
        assert config_path.is_file(), "trino-ingestion.yaml not found"
        return yaml.safe_load(config_path.read_text())

    def test_source_type_trino(self, ingestion_config):
        source = ingestion_config.get("source", {})
        assert source.get("type", "").lower() == "trino", (
            "source type should be 'trino'"
        )

    def test_service_name_set(self, ingestion_config):
        source = ingestion_config.get("source", {})
        assert source.get("serviceName") == "lakehouse-trino", (
            "serviceName should be 'lakehouse-trino'"
        )

    def test_host_port_references_trino(self, ingestion_config):
        source = ingestion_config.get("source", {})
        service_conn = source.get("serviceConnection", {})
        config = service_conn.get("config", {})
        host_port = config.get("hostPort", "")
        assert "trino" in host_port and "8080" in host_port, (
            f"hostPort should reference trino:8080, got '{host_port}'"
        )

    def test_catalog_is_iceberg(self, ingestion_config):
        source = ingestion_config.get("source", {})
        service_conn = source.get("serviceConnection", {})
        config = service_conn.get("config", {})
        assert config.get("catalog") == "iceberg", (
            "catalog should be 'iceberg'"
        )

    def test_schema_filter_includes_bronze_silver_gold(self, ingestion_config):
        source = ingestion_config.get("source", {})
        source_config = source.get("sourceConfig", {})
        config = source_config.get("config", {})
        schema_filter = config.get("schemaFilterPattern", {})
        includes = schema_filter.get("includes", [])
        includes_str = " ".join(includes)
        assert "bronze" in includes_str, "Schema filter should include bronze schemas"
        assert "silver" in includes_str, "Schema filter should include silver schemas"
        assert "gold" in includes_str, "Schema filter should include gold schemas"

    def test_sink_is_metadata_rest(self, ingestion_config):
        sink = ingestion_config.get("sink", {})
        assert sink.get("type") == "metadata-rest", (
            "sink type should be 'metadata-rest'"
        )

    def test_sink_host_references_openmetadata_server(self, ingestion_config):
        sink = ingestion_config.get("sink", {})
        config = sink.get("config", {})
        host_port = config.get("api_endpoint", "") or config.get("hostPort", "")
        assert "openmetadata-server" in host_port and "8585" in host_port, (
            f"sink hostPort should reference openmetadata-server:8585, got '{host_port}'"
        )

    def test_include_tables_true(self, ingestion_config):
        source = ingestion_config.get("source", {})
        source_config = source.get("sourceConfig", {})
        config = source_config.get("config", {})
        assert config.get("includeTables", False) is True, (
            "includeTables should be true"
        )

    def test_workflow_config_has_auth(self, ingestion_config):
        wf_config = ingestion_config.get("workflowConfig", {})
        open_metadata_server_config = wf_config.get("openMetadataServerConfig", {})
        auth_provider = open_metadata_server_config.get("authProvider", "")
        assert auth_provider == "openmetadata", (
            f"authProvider should be 'openmetadata', got '{auth_provider}'"
        )


@pytest.mark.unit
class TestGlossarySeedData:
    """Test that glossary seed JSON contains required FSDM terms."""

    @pytest.fixture(scope="class")
    def glossary_data(self):
        seed_path = (
            PROJECT_ROOT / "infra" / "docker" / "openmetadata" / "glossary-seed.json"
        )
        assert seed_path.is_file(), "glossary-seed.json not found"
        return json.loads(seed_path.read_text())

    def test_at_least_10_terms(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        assert len(terms) >= 10, f"Should have at least 10 FSDM terms, got {len(terms)}"

    def test_trade_term_exists(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        term_names = [t.get("name", "").lower() for t in terms]
        assert any("trade" in name for name in term_names), (
            "Glossary should contain 'Trade' term"
        )

    def test_position_term_exists(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        term_names = [t.get("name", "").lower() for t in terms]
        assert any("position" in name for name in term_names), (
            "Glossary should contain 'Position' term"
        )

    def test_pii_term_exists(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        term_names = [t.get("name", "").lower() for t in terms]
        assert any("pii" in name for name in term_names), (
            "Glossary should contain 'PII' term"
        )

    def test_bcbs_term_exists(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        term_names = [t.get("name", "").lower() for t in terms]
        assert any("bcbs" in name for name in term_names), (
            "Glossary should contain 'BCBS 239' term"
        )

    def test_terms_have_descriptions(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        for term in terms:
            assert term.get("description"), (
                f"Term '{term.get('name')}' should have a description"
            )

    def test_terms_have_draft_status(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        for term in terms:
            status = term.get("status", "")
            assert status == "Draft", (
                f"Term '{term.get('name')}' status should be 'Draft', got '{status}'"
            )

    def test_bronze_layer_term_exists(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        term_names = [t.get("name", "").lower() for t in terms]
        assert any("bronze" in name for name in term_names), (
            "Glossary should contain 'Bronze Layer' term"
        )

    def test_sla_term_exists(self, glossary_data):
        terms = glossary_data.get("terms", glossary_data) if isinstance(glossary_data, dict) else glossary_data
        term_names = [t.get("name", "").lower() for t in terms]
        assert any("sla" in name for name in term_names), (
            "Glossary should contain 'SLA' term"
        )

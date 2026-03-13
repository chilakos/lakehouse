"""Unit tests validating Ranger infrastructure configuration files.

Tests that docker-compose.yml has the correct Ranger services,
Trino config points to Ranger, event listener is configured,
and Ranger XML plugin files are correct.

No external services required -- runs on file system inspection only.
"""

from pathlib import Path

import pytest
import yaml


def _find_project_root() -> Path:
    """Find the project root by looking for .git directory or pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
        if (parent / "etl" / "pyproject.toml").exists():
            return parent
    return current.parent.parent.parent.parent


PROJECT_ROOT = _find_project_root()


@pytest.mark.unit
class TestDockerComposeRangerServices:
    """Test that Ranger services are correctly defined in docker-compose.yml."""

    @pytest.fixture(scope="class")
    def compose_data(self):
        compose_path = PROJECT_ROOT / "docker-compose.yml"
        assert compose_path.is_file(), "docker-compose.yml not found"
        return yaml.safe_load(compose_path.read_text())

    def test_ranger_db_service_exists(self, compose_data):
        assert "ranger-db" in compose_data["services"], "ranger-db service not found in docker-compose.yml"

    def test_ranger_solr_service_exists(self, compose_data):
        assert "ranger-solr" in compose_data["services"], "ranger-solr service not found in docker-compose.yml"

    def test_ranger_zk_service_exists(self, compose_data):
        assert "ranger-zk" in compose_data["services"], "ranger-zk service not found in docker-compose.yml"

    def test_ranger_admin_service_exists(self, compose_data):
        assert "ranger-admin" in compose_data["services"], "ranger-admin service not found in docker-compose.yml"

    def test_ranger_db_uses_postgres15(self, compose_data):
        ranger_db = compose_data["services"]["ranger-db"]
        assert ranger_db["image"].startswith("postgres:15"), "ranger-db should use postgres:15"

    def test_ranger_db_port_5435(self, compose_data):
        ranger_db = compose_data["services"]["ranger-db"]
        ports = ranger_db.get("ports", [])
        assert any("5435" in str(p) for p in ports), "ranger-db should be on port 5435"

    def test_ranger_admin_port_6080(self, compose_data):
        ranger_admin = compose_data["services"]["ranger-admin"]
        ports = ranger_admin.get("ports", [])
        assert any("6080" in str(p) for p in ports), "ranger-admin should expose port 6080"

    def test_ranger_admin_depends_on_db(self, compose_data):
        ranger_admin = compose_data["services"]["ranger-admin"]
        depends = ranger_admin.get("depends_on", {})
        if isinstance(depends, dict):
            assert "ranger-db" in depends, "ranger-admin should depend on ranger-db"
        else:
            assert "ranger-db" in depends, "ranger-admin should depend on ranger-db"

    def test_ranger_admin_has_db_env_vars(self, compose_data):
        ranger_admin = compose_data["services"]["ranger-admin"]
        env = ranger_admin.get("environment", {})
        if isinstance(env, list):
            env_str = " ".join(env)
            assert "DB_HOST" in env_str or "RANGER_DB" in env_str
        else:
            # dict form
            env_keys = list(env.keys())
            assert any("DB" in k for k in env_keys), "ranger-admin should have DB env vars"

    def test_no_port_conflicts(self, compose_data):
        """Verify no port conflicts with existing services."""
        used_ports = set()
        conflicting = []
        for svc_name, svc_config in compose_data["services"].items():
            for port_str in svc_config.get("ports", []):
                # Ports can be "5432:5432" or just "5432"
                host_port = str(port_str).split(":")[0] if ":" in str(port_str) else str(port_str)
                # strip /udp or /tcp
                host_port = host_port.split("/")[0].strip()
                if host_port in used_ports:
                    conflicting.append(f"{svc_name}: {host_port}")
                used_ports.add(host_port)
        assert not conflicting, f"Port conflicts detected: {conflicting}"

    def test_ranger_db_volume_defined(self, compose_data):
        volumes = compose_data.get("volumes", {})
        assert "ranger-db-data" in volumes, "ranger-db-data volume not defined"

    def test_trino_mounts_ranger_config(self, compose_data):
        trino = compose_data["services"]["trino"]
        trino_volumes = [str(v) for v in trino.get("volumes", [])]
        has_ranger_security = any("ranger-trino-security.xml" in v for v in trino_volumes)
        assert has_ranger_security, "Trino should mount ranger-trino-security.xml"

    def test_trino_mounts_event_listener(self, compose_data):
        trino = compose_data["services"]["trino"]
        trino_volumes = [str(v) for v in trino.get("volumes", [])]
        has_listener = any("event-listener.properties" in v for v in trino_volumes)
        assert has_listener, "Trino should mount event-listener.properties"


@pytest.mark.unit
class TestTrinoConfigProperties:
    """Test that Trino config.properties uses Ranger access control."""

    @pytest.fixture(scope="class")
    def trino_config(self):
        config_path = PROJECT_ROOT / "infra" / "docker" / "trino" / "etc" / "config.properties"
        assert config_path.is_file(), "Trino config.properties not found"
        return config_path.read_text()

    def test_ranger_access_control_set(self, trino_config):
        assert "access-control.name=ranger" in trino_config, (
            "Trino config.properties should use 'access-control.name=ranger'"
        )

    def test_file_based_rbac_removed(self, trino_config):
        # Should not have uncommented file-based RBAC
        lines = trino_config.splitlines()
        active_lines = [l for l in lines if l.strip() and not l.strip().startswith("#")]
        for line in active_lines:
            assert "access-control.name=file" not in line, (
                "File-based RBAC should be commented out, not active"
            )

    def test_ranger_service_name_set(self, trino_config):
        assert "ranger.service.name" in trino_config or "ranger.plugin" in trino_config, (
            "Trino config should reference Ranger service name"
        )


@pytest.mark.unit
class TestEventListenerProperties:
    """Test that event-listener.properties has correct HTTP endpoint config."""

    @pytest.fixture(scope="class")
    def event_listener_config(self):
        config_path = (
            PROJECT_ROOT / "infra" / "docker" / "trino" / "etc" / "event-listener.properties"
        )
        assert config_path.is_file(), "event-listener.properties not found"
        return config_path.read_text()

    def test_event_listener_name_http(self, event_listener_config):
        assert "event-listener.name=http" in event_listener_config

    def test_ingest_uri_set(self, event_listener_config):
        assert "http-event-listener.connect-ingest-uri" in event_listener_config

    def test_log_completed_true(self, event_listener_config):
        assert "http-event-listener.log-completed=true" in event_listener_config


@pytest.mark.unit
class TestRangerPluginXml:
    """Test that Ranger plugin XML config files exist and contain required settings."""

    def test_ranger_trino_security_xml_exists(self):
        xml_path = PROJECT_ROOT / "infra" / "docker" / "ranger" / "ranger-trino-security.xml"
        assert xml_path.is_file(), "ranger-trino-security.xml not found"

    def test_ranger_trino_audit_xml_exists(self):
        xml_path = PROJECT_ROOT / "infra" / "docker" / "ranger" / "ranger-trino-audit.xml"
        assert xml_path.is_file(), "ranger-trino-audit.xml not found"

    def test_ranger_install_properties_exists(self):
        props_path = PROJECT_ROOT / "infra" / "docker" / "ranger" / "install.properties"
        assert props_path.is_file(), "install.properties not found"

    def test_ranger_security_xml_has_service_name(self):
        xml_path = PROJECT_ROOT / "infra" / "docker" / "ranger" / "ranger-trino-security.xml"
        content = xml_path.read_text()
        assert "ranger.plugin.trino" in content or "trino" in content, (
            "ranger-trino-security.xml should reference trino plugin"
        )

    def test_ranger_security_xml_has_policy_url(self):
        xml_path = PROJECT_ROOT / "infra" / "docker" / "ranger" / "ranger-trino-security.xml"
        content = xml_path.read_text()
        assert "6080" in content or "ranger-admin" in content, (
            "ranger-trino-security.xml should reference Ranger admin URL"
        )

    def test_ranger_audit_xml_has_solr_url(self):
        xml_path = PROJECT_ROOT / "infra" / "docker" / "ranger" / "ranger-trino-audit.xml"
        content = xml_path.read_text()
        assert "solr" in content.lower() or "ranger_audits" in content, (
            "ranger-trino-audit.xml should reference Solr audit URL"
        )

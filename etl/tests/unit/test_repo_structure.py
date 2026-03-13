"""Unit tests validating the mono-repo directory structure.

These tests verify that the repository layout matches the locked decision:
mono-repo with /infra, /etl, /dbt, /ci, /docs top-level folders.

No external services required -- runs on file system inspection only.
"""

from pathlib import Path

import pytest


def _find_project_root() -> Path:
    """Find the project root by looking for .git directory or pyproject.toml."""
    # Start from this file's location and walk up
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
        if (parent / "etl" / "pyproject.toml").exists():
            return parent
    # Fallback: assume we are in etl/tests/unit/
    return current.parent.parent.parent.parent


PROJECT_ROOT = _find_project_root()


@pytest.mark.unit
class TestTopLevelStructure:
    """Test that top-level directories exist per the mono-repo layout."""

    @pytest.mark.parametrize("dirname", ["infra", "etl", "dbt", "ci", "docs"])
    def test_top_level_directories_exist(self, dirname: str):
        path = PROJECT_ROOT / dirname
        assert path.is_dir(), f"Top-level directory '{dirname}/' is missing"


@pytest.mark.unit
class TestTerraformStructure:
    """Test Terraform scaffolding files and directories."""

    def test_terraform_main_tf(self):
        assert (PROJECT_ROOT / "infra" / "terraform" / "main.tf").is_file()

    def test_terraform_variables_tf(self):
        assert (PROJECT_ROOT / "infra" / "terraform" / "variables.tf").is_file()

    def test_terraform_outputs_tf(self):
        assert (PROJECT_ROOT / "infra" / "terraform" / "outputs.tf").is_file()

    def test_terraform_backend_tf(self):
        assert (PROJECT_ROOT / "infra" / "terraform" / "backend.tf").is_file()

    def test_terraform_modules_dir(self):
        assert (PROJECT_ROOT / "infra" / "terraform" / "modules").is_dir()

    @pytest.mark.parametrize("env", ["dev", "staging", "prod"])
    def test_terraform_environments(self, env: str):
        tfvars = PROJECT_ROOT / "infra" / "terraform" / "environments" / env / "terraform.tfvars"
        assert tfvars.is_file(), f"Missing terraform.tfvars for environment '{env}'"


@pytest.mark.unit
class TestEtlPythonStructure:
    """Test Python ETL project structure."""

    def test_pyproject_toml(self):
        assert (PROJECT_ROOT / "etl" / "pyproject.toml").is_file()

    def test_src_directory(self):
        assert (PROJECT_ROOT / "etl" / "src").is_dir()

    def test_tests_directory(self):
        assert (PROJECT_ROOT / "etl" / "tests").is_dir()

    def test_config_module(self):
        assert (PROJECT_ROOT / "etl" / "src" / "config" / "__init__.py").is_file()

    def test_synthetic_module(self):
        assert (PROJECT_ROOT / "etl" / "src" / "synthetic" / "__init__.py").is_file()

    def test_iceberg_utils_module(self):
        assert (PROJECT_ROOT / "etl" / "src" / "iceberg_utils" / "__init__.py").is_file()


@pytest.mark.unit
class TestCiWorkflows:
    """Test CI/CD workflow configuration."""

    def test_ci_workflow_exists(self):
        assert (PROJECT_ROOT / "ci" / ".github" / "workflows" / "ci.yml").is_file()


@pytest.mark.unit
class TestGitignore:
    """Test that .gitignore contains essential patterns."""

    @pytest.fixture()
    def gitignore_content(self) -> str:
        gitignore_path = PROJECT_ROOT / ".gitignore"
        assert gitignore_path.is_file(), ".gitignore file is missing"
        return gitignore_path.read_text()

    @pytest.mark.parametrize(
        "pattern",
        [
            "*.tfstate",
            "__pycache__",
            ".env",
            ".terraform/",
            "*.egg-info",
            ".venv",
        ],
    )
    def test_gitignore_patterns(self, gitignore_content: str, pattern: str):
        assert pattern in gitignore_content, f".gitignore missing pattern: {pattern}"


@pytest.mark.unit
class TestDockerComposeFiles:
    """Test Docker Compose files exist and reference expected services."""

    def test_docker_compose_yml_exists(self):
        assert (PROJECT_ROOT / "docker-compose.yml").is_file()

    def test_docker_compose_test_yml_exists(self):
        assert (PROJECT_ROOT / "docker-compose.test.yml").is_file()

    def test_docker_compose_contains_nessie(self):
        content = (PROJECT_ROOT / "docker-compose.yml").read_text()
        assert "nessie" in content, "docker-compose.yml should reference nessie service"

    def test_docker_compose_test_contains_nessie(self):
        content = (PROJECT_ROOT / "docker-compose.test.yml").read_text()
        assert "nessie" in content, "docker-compose.test.yml should reference nessie service"

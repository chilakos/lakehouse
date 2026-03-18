"""Unit tests for RiskExposureGoldPipeline.

Validates that the risk exposure Gold pipeline extends BasePipeline,
targets the GOLD layer, and has the correct schema with appropriate
decimal types for financial fields.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
class TestRiskExposurePipelineStructure:
    """Test RiskExposureGoldPipeline class structure."""

    def test_risk_exposure_pipeline_extends_base(self):
        """RiskExposureGoldPipeline extends BasePipeline."""
        from src.pipelines.base import BasePipeline
        from src.pipelines.gold.risk_exposure import RiskExposureGoldPipeline

        assert issubclass(RiskExposureGoldPipeline, BasePipeline)

    def test_risk_exposure_pipeline_gold_layer(self):
        """pipeline config target_layer is MedallionLayer.GOLD."""
        from src.pipelines.base import MedallionLayer
        from src.pipelines.gold.risk_exposure import RiskExposureGoldPipeline

        pipeline = RiskExposureGoldPipeline(spark=MagicMock())
        assert pipeline.config.target_layer == MedallionLayer.GOLD

    def test_risk_exposure_pipeline_target_table(self):
        """pipeline config target_table is risk_exposure."""
        from src.pipelines.gold.risk_exposure import RiskExposureGoldPipeline

        pipeline = RiskExposureGoldPipeline(spark=MagicMock())
        assert pipeline.config.target_table == "risk_exposure"
        assert pipeline.config.full_table_name == "lakehouse.gold.risk_exposure"


@pytest.mark.unit
class TestRiskExposurePipelineSchema:
    """Test the Gold schema for risk exposure."""

    def test_risk_exposure_pipeline_schema(self):
        """Gold schema has expected risk exposure fields.

        Checks account_id, sector, currency, total_market_value,
        total_var_95, total_var_99, total_expected_shortfall, position_count.
        """
        from src.pipelines.gold.risk_exposure import RiskExposureGoldPipeline

        pipeline = RiskExposureGoldPipeline(spark=MagicMock())
        field_names = {f.name for f in pipeline.config.target_schema.fields}

        expected_fields = {
            "account_id",
            "sector",
            "currency",
            "total_market_value",
            "total_var_95",
            "total_var_99",
            "total_expected_shortfall",
            "position_count",
        }
        assert expected_fields == field_names, f"Schema fields mismatch: expected {expected_fields}, got {field_names}"

    def test_risk_exposure_pipeline_uses_decimal(self):
        """financial fields use DecimalType(38,4) or DecimalType(18,2)."""
        from pyspark.sql.types import DecimalType, LongType

        from src.pipelines.gold.risk_exposure import RiskExposureGoldPipeline

        pipeline = RiskExposureGoldPipeline(spark=MagicMock())
        fields = {f.name: f.dataType for f in pipeline.config.target_schema.fields}

        # total_market_value uses DecimalType(38, 4) -- high-precision aggregation
        assert fields["total_market_value"] == DecimalType(38, 4), (
            f"total_market_value should be DecimalType(38,4), got {fields['total_market_value']}"
        )

        # VaR and ES fields use DecimalType(18, 2)
        assert fields["total_var_95"] == DecimalType(18, 2)
        assert fields["total_var_99"] == DecimalType(18, 2)
        assert fields["total_expected_shortfall"] == DecimalType(18, 2)

        # position_count is LongType
        assert fields["position_count"] == LongType()


@pytest.mark.unit
class TestPyprojectDependencies:
    """Test that pyproject.toml has required dependencies."""

    def _load_pyproject(self):
        from pathlib import Path

        return (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text()

    def test_pyproject_has_pyyaml(self):
        """pyproject.toml includes pyyaml dependency."""
        content = self._load_pyproject()
        assert "pyyaml" in content.lower(), "pyyaml not found in pyproject.toml dependencies"

    def test_pyproject_has_pytest_benchmark(self):
        """pyproject.toml includes pytest-benchmark in dev deps."""
        content = self._load_pyproject()
        assert "pytest-benchmark" in content.lower(), "pytest-benchmark not found in pyproject.toml dev dependencies"

"""Soda Core scanner utility for DataFrame quality checks.

Wraps soda-core-spark-df to run SodaCL checks against PySpark DataFrames.
Uses the programmatic scan API (no configuration.yml needed for DF scans).

Usage:
    from src.quality.scanner import run_soda_checks, QualityCheckResult

    results = run_soda_checks(
        spark_session=spark,
        df=my_dataframe,
        checks_yaml_path="src/quality/checks/bronze_trades.yml",
        critical_check_names=["primary_key_not_null", "primary_key_unique"],
    )
    if not results["passed"]:
        handle_failures(results["critical_failures"])
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pyspark.sql import DataFrame, SparkSession

logger = logging.getLogger(__name__)


@dataclass
class QualityCheckResult:
    """Result of a single quality check execution.

    Attributes:
        check_name: Human-readable name of the check.
        outcome: Check result -- "pass", "fail", or "warn".
        metric_value: Actual metric value observed.
        threshold: Expected threshold or constraint.
        is_critical: Whether this check blocks pipeline progression.
    """

    check_name: str
    outcome: str  # "pass" | "fail" | "warn"
    metric_value: Any
    threshold: Any
    is_critical: bool

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for JSON/alerting integration."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON string for alerting systems (e.g., Grafana)."""
        return json.dumps(self.to_dict(), default=str)


def run_soda_checks(
    spark_session: SparkSession,
    df: DataFrame,
    checks_yaml_path: str,
    critical_check_names: list[str] | None = None,
    data_source_name: str = "spark_df",
) -> dict[str, Any]:
    """Run Soda Core quality checks on a PySpark DataFrame.

    Uses Soda Core's programmatic scan API for DataFrames. Does NOT use
    configuration.yml -- passes SparkSession directly via scan.add_spark_session().

    Args:
        spark_session: Active SparkSession.
        df: PySpark DataFrame to check.
        checks_yaml_path: Path to SodaCL YAML check definitions file.
        critical_check_names: List of check names that constitute critical failures.
            If None, defaults to empty list (all checks are advisory).
        data_source_name: Name for the Soda data source (default: "spark_df").

    Returns:
        Dict with:
            passed (bool): True if no critical checks failed.
            critical_failures (list[QualityCheckResult]): Critical checks that failed.
            warnings (list[QualityCheckResult]): Non-critical checks that failed/warned.
            all_results (list[QualityCheckResult]): All check results.
    """
    from soda.scan import Scan

    if critical_check_names is None:
        critical_check_names = []

    scan = Scan()
    scan.set_scan_definition_name("etl_quality_gate")
    scan.set_data_source_name(data_source_name)
    scan.add_spark_session(spark_session, data_source_name)
    scan.disable_telemetry()

    # Create a temp view for the DataFrame so SodaCL checks can reference it
    temp_view_name = "__soda_check_target"
    df.createOrReplaceTempView(temp_view_name)

    # Load the SodaCL YAML check definitions
    scan.add_sodacl_yaml_file(checks_yaml_path)

    logger.info("Executing Soda scan with checks from %s", checks_yaml_path)
    scan.execute()

    # Parse results from the scan
    all_results: list[QualityCheckResult] = []
    critical_failures: list[QualityCheckResult] = []
    warnings: list[QualityCheckResult] = []

    for check in scan._checks:
        check_name = getattr(check, "name", None) or str(check.check_cfg)
        outcome = str(check.outcome.value).lower() if check.outcome else "unknown"

        # Extract metric value and threshold from check diagnostics
        metric_value = None
        threshold = None
        if hasattr(check, "check_value"):
            metric_value = check.check_value
        diagnostics = getattr(check, "diagnostics", None)
        if diagnostics:
            blocks = getattr(diagnostics, "blocks", [])
            for block in blocks:
                if hasattr(block, "text"):
                    threshold = block.text

        is_critical = check_name in critical_check_names

        result = QualityCheckResult(
            check_name=check_name,
            outcome=outcome,
            metric_value=metric_value,
            threshold=threshold,
            is_critical=is_critical,
        )
        all_results.append(result)

        if outcome == "fail":
            if is_critical:
                critical_failures.append(result)
                logger.error("CRITICAL quality check failed: %s", check_name)
            else:
                warnings.append(result)
                logger.warning("Advisory quality check failed: %s", check_name)
        elif outcome == "warn":
            warnings.append(result)
            logger.warning("Quality check warning: %s", check_name)

    passed = len(critical_failures) == 0

    logger.info(
        "Soda scan complete: passed=%s, critical_failures=%d, warnings=%d, total_checks=%d",
        passed,
        len(critical_failures),
        len(warnings),
        len(all_results),
    )

    return {
        "passed": passed,
        "critical_failures": critical_failures,
        "warnings": warnings,
        "all_results": all_results,
    }

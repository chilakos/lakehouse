"""Integration tests for NL-to-SQL accuracy evaluation.

Tests require AWS Bedrock access (BEDROCK_AVAILABLE env var or AWS
credentials) and a running Trino instance. All tests auto-skip when
dependencies are not available.

These tests validate:
- NL-to-SQL accuracy on trading golden dataset (simple >= 90%, complex >= 70%)
- NL-to-SQL accuracy on risk exposure golden dataset (same thresholds)

Usage:
    # Set AWS credentials and start Trino:
    export BEDROCK_AVAILABLE=true
    docker compose up -d trino minio nessie

    # Run integration tests:
    cd etl && python -m pytest tests/integration/test_nl_accuracy.py -v
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

TRINO_HOST = os.environ.get("TRINO_HOST", "localhost")
TRINO_PORT = int(os.environ.get("TRINO_PORT", "8080"))

# Golden dataset paths
REPO_ROOT = Path(__file__).resolve().parents[3]
TRADING_DATASET = REPO_ROOT / "etl" / "src" / "semantic" / "golden_datasets" / "trading_questions.json"
RISK_DATASET = REPO_ROOT / "etl" / "src" / "semantic" / "golden_datasets" / "risk_questions.json"
MODEL_DIR = str(REPO_ROOT / "semantic" / "model")


def _trino_available() -> bool:
    """TCP probe to check if Trino is reachable."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((TRINO_HOST, TRINO_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False


def _bedrock_available() -> bool:
    """Check if Bedrock is available via env var or AWS credentials."""
    if os.environ.get("BEDROCK_AVAILABLE", "").lower() in ("true", "1", "yes"):
        return True
    # Check for AWS credentials
    return bool(
        os.environ.get("AWS_ACCESS_KEY_ID")
        or os.environ.get("AWS_SESSION_TOKEN")
        or os.environ.get("AWS_PROFILE")
    )


# Skip all tests when Bedrock or Trino not available
pytestmark = [
    pytest.mark.skipif(
        not _bedrock_available(),
        reason="AWS Bedrock not available (set BEDROCK_AVAILABLE=true or AWS credentials)",
    ),
    pytest.mark.skipif(
        not _trino_available(),
        reason=f"Trino not available at {TRINO_HOST}:{TRINO_PORT}",
    ),
]


def _get_trino_connection():
    """Create a Trino DBAPI connection."""
    from src.iceberg_utils.trino import get_trino_connection

    return get_trino_connection(
        host=TRINO_HOST,
        port=TRINO_PORT,
    )


def _get_engine():
    """Create an NLToSQLEngine instance."""
    from src.semantic.nl_to_sql import NLToSQLEngine

    return NLToSQLEngine(model_dir=MODEL_DIR)


@pytest.mark.integration
class TestNLAccuracyTrading:
    """NL-to-SQL accuracy tests for the trading domain."""

    def test_nl_accuracy_trading_simple(self):
        """Run evaluation on trading golden dataset, simple only, assert >= 90%."""
        from src.semantic.evaluation import (
            evaluate_accuracy,
            load_golden_dataset,
            run_evaluation,
        )

        engine = _get_engine()
        conn = _get_trino_connection()
        dataset = load_golden_dataset(str(TRADING_DATASET))

        # Filter to simple only
        simple_dataset = [d for d in dataset if d["complexity"] == "simple"]
        results = run_evaluation(engine, conn, simple_dataset)
        accuracy = evaluate_accuracy(results)

        assert accuracy["accuracy_pct"] >= 90.0, (
            f"Trading simple accuracy {accuracy['accuracy_pct']}% < 90% threshold"
        )

    def test_nl_accuracy_trading_complex(self):
        """Run evaluation on trading golden dataset, complex only, assert >= 70%."""
        from src.semantic.evaluation import (
            evaluate_accuracy,
            load_golden_dataset,
            run_evaluation,
        )

        engine = _get_engine()
        conn = _get_trino_connection()
        dataset = load_golden_dataset(str(TRADING_DATASET))

        # Filter to complex only
        complex_dataset = [d for d in dataset if d["complexity"] == "complex"]
        results = run_evaluation(engine, conn, complex_dataset)
        accuracy = evaluate_accuracy(results)

        assert accuracy["accuracy_pct"] >= 70.0, (
            f"Trading complex accuracy {accuracy['accuracy_pct']}% < 70% threshold"
        )


@pytest.mark.integration
class TestNLAccuracyRisk:
    """NL-to-SQL accuracy tests for the risk exposure domain."""

    def test_nl_accuracy_risk_simple(self):
        """Run evaluation on risk golden dataset, simple only, assert >= 90%."""
        from src.semantic.evaluation import (
            evaluate_accuracy,
            load_golden_dataset,
            run_evaluation,
        )

        engine = _get_engine()
        conn = _get_trino_connection()
        dataset = load_golden_dataset(str(RISK_DATASET))

        simple_dataset = [d for d in dataset if d["complexity"] == "simple"]
        results = run_evaluation(engine, conn, simple_dataset)
        accuracy = evaluate_accuracy(results)

        assert accuracy["accuracy_pct"] >= 90.0, (
            f"Risk simple accuracy {accuracy['accuracy_pct']}% < 90% threshold"
        )

    def test_nl_accuracy_risk_complex(self):
        """Run evaluation on risk golden dataset, complex only, assert >= 70%."""
        from src.semantic.evaluation import (
            evaluate_accuracy,
            load_golden_dataset,
            run_evaluation,
        )

        engine = _get_engine()
        conn = _get_trino_connection()
        dataset = load_golden_dataset(str(RISK_DATASET))

        complex_dataset = [d for d in dataset if d["complexity"] == "complex"]
        results = run_evaluation(engine, conn, complex_dataset)
        accuracy = evaluate_accuracy(results)

        assert accuracy["accuracy_pct"] >= 70.0, (
            f"Risk complex accuracy {accuracy['accuracy_pct']}% < 70% threshold"
        )

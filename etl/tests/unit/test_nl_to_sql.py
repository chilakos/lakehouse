"""Tests for NL-to-SQL engine.

Validates that the NL-to-SQL engine generates SQL via Claude on Bedrock
with proper error handling, markdown fence stripping, and metric context
integration. All LLM calls are mocked.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.semantic.nl_to_sql import NLToSQLEngine, NLToSQLError


def _make_bedrock_response(sql_text: str) -> dict:
    """Create a mock Bedrock invoke_model response body."""
    body = json.dumps({"content": [{"text": sql_text}]})
    mock_body = MagicMock()
    mock_body.read.return_value = body.encode("utf-8")
    return {"body": mock_body}


class TestGenerateSQL:
    """Validate generate_sql function behavior with mocked Bedrock."""

    @patch("src.semantic.nl_to_sql.boto3")
    @patch("src.semantic.nl_to_sql.load_cube_definitions")
    @patch("src.semantic.nl_to_sql.build_metric_context")
    def test_generate_sql_calls_bedrock(self, mock_ctx, mock_load, mock_boto3):
        """generate_sql must invoke bedrock-runtime client."""
        mock_load.return_value = [{"name": "trading_metrics", "type": "cube"}]
        mock_ctx.return_value = "TABLE: gold.trading_metrics"
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.return_value = _make_bedrock_response("SELECT * FROM gold.trading_metrics")

        engine = NLToSQLEngine(model_dir="semantic/model")
        engine.ask("How many trades?")

        mock_boto3.client.assert_called_once_with("bedrock-runtime", region_name="us-east-1")
        mock_client.invoke_model.assert_called_once()
        call_kwargs = mock_client.invoke_model.call_args[1]
        assert "modelId" in call_kwargs

    @patch("src.semantic.nl_to_sql.boto3")
    @patch("src.semantic.nl_to_sql.load_cube_definitions")
    @patch("src.semantic.nl_to_sql.build_metric_context")
    def test_generate_sql_returns_sql_string(self, mock_ctx, mock_load, mock_boto3):
        """generate_sql must return a SQL string from the mocked response."""
        mock_load.return_value = []
        mock_ctx.return_value = ""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        expected_sql = "SELECT SUM(total_notional) FROM gold.trading_metrics"
        mock_client.invoke_model.return_value = _make_bedrock_response(expected_sql)

        engine = NLToSQLEngine(model_dir="semantic/model")
        result = engine.ask("What is the total notional?")

        assert result == expected_sql

    @patch("src.semantic.nl_to_sql.boto3")
    @patch("src.semantic.nl_to_sql.load_cube_definitions")
    @patch("src.semantic.nl_to_sql.build_metric_context")
    def test_generate_sql_strips_markdown_fences(self, mock_ctx, mock_load, mock_boto3):
        """If LLM returns ```sql...```, the fences must be stripped."""
        mock_load.return_value = []
        mock_ctx.return_value = ""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        fenced = "```sql\nSELECT * FROM gold.trading_metrics\n```"
        mock_client.invoke_model.return_value = _make_bedrock_response(fenced)

        engine = NLToSQLEngine(model_dir="semantic/model")
        result = engine.ask("Show all trades")

        assert result == "SELECT * FROM gold.trading_metrics"
        assert "```" not in result

    @patch("src.semantic.nl_to_sql.boto3")
    @patch("src.semantic.nl_to_sql.load_cube_definitions")
    @patch("src.semantic.nl_to_sql.build_metric_context")
    def test_generate_sql_uses_metric_context(self, mock_ctx, mock_load, mock_boto3):
        """generate_sql must call build_metric_context with loaded definitions."""
        defs = [{"name": "trading_metrics", "type": "cube"}]
        mock_load.return_value = defs
        mock_ctx.return_value = "TABLE: gold.trading_metrics"
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.return_value = _make_bedrock_response("SELECT 1")

        engine = NLToSQLEngine(model_dir="semantic/model")
        engine.ask("test")

        mock_load.assert_called_once_with("semantic/model")
        mock_ctx.assert_called_once_with(defs)


class TestNLToSQLEngine:
    """Validate NLToSQLEngine initialization and ask method."""

    def test_nl_to_sql_engine_init(self):
        """NLToSQLEngine must initialize with model_dir and optional bedrock config."""
        engine = NLToSQLEngine(model_dir="semantic/model")
        assert engine.model_dir == "semantic/model"
        assert engine.region_name == "us-east-1"
        assert "claude" in engine.model_id.lower() or "anthropic" in engine.model_id.lower()

    def test_nl_to_sql_engine_custom_config(self):
        """NLToSQLEngine must accept custom region and model_id."""
        engine = NLToSQLEngine(
            model_dir="semantic/model",
            region_name="eu-west-1",
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
        )
        assert engine.region_name == "eu-west-1"
        assert engine.model_id == "anthropic.claude-3-haiku-20240307-v1:0"

    @patch("src.semantic.nl_to_sql.boto3")
    @patch("src.semantic.nl_to_sql.load_cube_definitions")
    @patch("src.semantic.nl_to_sql.build_metric_context")
    def test_nl_to_sql_engine_ask(self, mock_ctx, mock_load, mock_boto3):
        """engine.ask(question) must return a SQL string."""
        mock_load.return_value = []
        mock_ctx.return_value = ""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.return_value = _make_bedrock_response("SELECT COUNT(*) FROM gold.trading_metrics")

        engine = NLToSQLEngine(model_dir="semantic/model")
        result = engine.ask("How many trades?")

        assert isinstance(result, str)
        assert "SELECT" in result

    @patch("src.semantic.nl_to_sql.boto3")
    @patch("src.semantic.nl_to_sql.load_cube_definitions")
    @patch("src.semantic.nl_to_sql.build_metric_context")
    def test_nl_to_sql_engine_ask_with_domain(self, mock_ctx, mock_load, mock_boto3):
        """engine.ask(question, domain='trading') must use domain-specific few-shot examples."""
        mock_load.return_value = []
        mock_ctx.return_value = ""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.return_value = _make_bedrock_response(
            "SELECT SUM(total_notional) FROM gold.trading_metrics"
        )

        engine = NLToSQLEngine(model_dir="semantic/model")
        result = engine.ask("What is the total notional?", domain="trading")

        assert isinstance(result, str)
        # Verify that domain was passed through by checking invoke_model was called
        # with a body containing the few-shot examples
        call_kwargs = mock_client.invoke_model.call_args[1]
        body = json.loads(call_kwargs["body"])
        system_content = body["system"]
        assert "gold.trading_metrics" in system_content

    @patch("src.semantic.nl_to_sql.boto3")
    @patch("src.semantic.nl_to_sql.load_cube_definitions")
    @patch("src.semantic.nl_to_sql.build_metric_context")
    def test_nl_to_sql_error_on_bedrock_failure(self, mock_ctx, mock_load, mock_boto3):
        """NLToSQLError must be raised when Bedrock call fails."""
        mock_load.return_value = []
        mock_ctx.return_value = ""
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.invoke_model.side_effect = Exception("Bedrock service error")

        engine = NLToSQLEngine(model_dir="semantic/model")
        with pytest.raises(NLToSQLError):
            engine.ask("test question")

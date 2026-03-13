"""Tests for NL-to-SQL prompt builder.

Validates that the prompt builder constructs properly structured LLM messages
with Cube YAML metric context and domain-specific few-shot examples.
"""

from __future__ import annotations

import pytest

from src.semantic.prompt_builder import (
    SYSTEM_PROMPT,
    build_few_shot_examples,
    build_prompt,
)


class TestSystemPromptTemplate:
    """Validate SYSTEM_PROMPT template structure and required content."""

    def test_system_prompt_contains_metric_context(self):
        """SYSTEM_PROMPT template must have {metric_context} placeholder."""
        assert "{metric_context}" in SYSTEM_PROMPT

    def test_system_prompt_contains_few_shot(self):
        """SYSTEM_PROMPT template must have {few_shot_examples} placeholder."""
        assert "{few_shot_examples}" in SYSTEM_PROMPT

    def test_system_prompt_contains_decimal_rule(self):
        """System prompt must mention DECIMAL types and no floating point."""
        # Check case-insensitively for flexibility
        lower = SYSTEM_PROMPT.lower()
        assert "decimal" in lower
        assert "float" in lower  # "no floating point" or similar

    def test_system_prompt_contains_schema_qualification(self):
        """System prompt must require gold.table_name qualification."""
        assert "gold." in SYSTEM_PROMPT


class TestBuildPrompt:
    """Validate build_prompt returns correctly structured messages."""

    def test_build_prompt_returns_messages(self):
        """build_prompt must return a list of dicts with 'role' and 'content' keys."""
        messages = build_prompt(
            question="What is the total notional?",
            metric_context="TABLE: gold.trading_metrics",
            few_shot_examples="Q: How many trades?\nA: SELECT count(*) FROM gold.trading_metrics",
        )
        assert isinstance(messages, list)
        assert len(messages) >= 2
        for msg in messages:
            assert "role" in msg
            assert "content" in msg

    def test_build_prompt_system_message_has_context(self):
        """First message must be 'system' role and contain the metric_context arg."""
        context = "TABLE: gold.trading_metrics\n  METRIC: total_notional (type=sum)"
        messages = build_prompt(
            question="test question",
            metric_context=context,
            few_shot_examples="",
        )
        assert messages[0]["role"] == "system"
        assert context in messages[0]["content"]

    def test_build_prompt_user_message_has_question(self):
        """Second message must be 'user' role and contain the question."""
        question = "What is the average price for AAPL?"
        messages = build_prompt(
            question=question,
            metric_context="some context",
            few_shot_examples="",
        )
        assert messages[1]["role"] == "user"
        assert question in messages[1]["content"]


class TestBuildFewShotExamples:
    """Validate build_few_shot_examples returns domain-specific Q&A pairs."""

    def test_build_few_shot_examples_trading(self):
        """build_few_shot_examples('trading') returns formatted Q&A pairs."""
        examples = build_few_shot_examples("trading")
        assert isinstance(examples, str)
        assert len(examples) > 0
        # Should reference the trading table
        assert "gold.trading_metrics" in examples

    def test_build_few_shot_examples_risk(self):
        """build_few_shot_examples('risk_exposure') returns formatted Q&A pairs."""
        examples = build_few_shot_examples("risk_exposure")
        assert isinstance(examples, str)
        assert len(examples) > 0
        # Should reference the risk exposure table
        assert "gold.risk_exposure" in examples

    def test_build_few_shot_examples_none_domain(self):
        """build_few_shot_examples(None) returns empty string or generic."""
        examples = build_few_shot_examples(None)
        assert isinstance(examples, str)

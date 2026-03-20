"""NL-to-SQL engine using Claude via AWS Bedrock.

Generates Trino SQL from natural language questions by combining Cube YAML
metric definitions (via metric_context.py) with domain-specific few-shot
examples in a structured LLM prompt. This is the core NL-to-SQL capability
required by AISEM-01.

Usage:
    engine = NLToSQLEngine(model_dir="semantic/model")
    sql = engine.ask("What is the total notional for AAPL?", domain="trading")
"""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

import boto3

from src.semantic.metric_context import build_metric_context, load_cube_definitions
from src.semantic.prompt_builder import build_few_shot_examples, build_prompt

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Regex to strip markdown SQL fences from LLM output
_FENCE_PATTERN = re.compile(r"^```(?:sql)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


class NLToSQLError(Exception):
    """Raised when NL-to-SQL generation fails."""


class NLToSQLEngine:
    """NL-to-SQL engine that generates Trino SQL via Claude on Bedrock.

    Combines Cube YAML metric definitions with domain-specific few-shot
    examples to produce accurate SQL from natural language questions.

    Args:
        model_dir: Path to the Cube model directory (e.g., "semantic/model").
        region_name: AWS region for Bedrock (default "us-east-1").
        model_id: Bedrock model identifier (default Claude Sonnet).
    """

    def __init__(
        self,
        model_dir: str,
        region_name: str = "us-east-1",
        model_id: str = "anthropic.claude-sonnet-4-20250514-v1:0",
    ) -> None:
        self.model_dir = model_dir
        self.region_name = region_name
        self.model_id = model_id

    def generate_sql(self, question: str, domain: str | None = None) -> str:
        """Generate Trino SQL from a natural language question.

        Loads Cube metric definitions, builds a structured LLM prompt with
        metric context and domain-specific few-shot examples, and invokes
        Claude on Bedrock to generate SQL.

        Args:
            question: Natural language question about the data.
            domain: Optional domain for few-shot examples ('trading' or
                'risk_exposure'). If None, no domain-specific examples
                are included.

        Returns:
            Clean SQL string (markdown fences stripped).

        Raises:
            NLToSQLError: If the Bedrock API call fails.
        """
        # Load Cube definitions and build metric context
        definitions = load_cube_definitions(self.model_dir)
        metric_context = build_metric_context(definitions)

        # Build few-shot examples for the domain
        few_shot_examples = build_few_shot_examples(domain)

        # Build the prompt messages
        messages = build_prompt(question, metric_context, few_shot_examples)

        # Extract system and user content from messages
        system_content = messages[0]["content"]
        user_message = messages[1]["content"]

        # Call Bedrock
        try:
            client = boto3.client("bedrock-runtime", region_name=self.region_name)
            body = json.dumps(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1024,
                    "system": system_content,
                    "messages": [{"role": "user", "content": user_message}],
                }
            )

            response = client.invoke_model(
                modelId=self.model_id,
                body=body,
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            raw_sql = response_body["content"][0]["text"]

        except NLToSQLError:
            raise
        except Exception as exc:
            raise NLToSQLError(f"Bedrock API call failed: {exc}") from exc

        return _strip_markdown_fences(raw_sql)

    def ask(self, question: str, domain: str | None = None) -> str:
        """Convenience wrapper for generate_sql.

        Args:
            question: Natural language question about the data.
            domain: Optional domain for few-shot examples.

        Returns:
            Clean SQL string.

        Raises:
            NLToSQLError: If SQL generation fails.
        """
        return self.generate_sql(question, domain=domain)


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM output.

    Handles patterns like:
        ```sql
        SELECT ...
        ```

    Args:
        text: Raw LLM output that may contain markdown fences.

    Returns:
        Clean SQL text with fences removed.
    """
    text = text.strip()
    match = _FENCE_PATTERN.match(text)
    if match:
        return match.group(1).strip()
    return text

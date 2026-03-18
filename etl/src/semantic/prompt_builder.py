"""NL-to-SQL prompt builder with Cube YAML metric context injection.

Constructs structured LLM prompts that embed Cube semantic layer metric
definitions as context, enabling the LLM to generate accurate Trino SQL
from natural language questions. Domain-specific few-shot examples guide
the LLM toward correct SQL patterns for each pilot domain.

Usage:
    from src.semantic.metric_context import load_cube_definitions, build_metric_context
    from src.semantic.prompt_builder import build_prompt, build_few_shot_examples

    defs = load_cube_definitions("semantic/model")
    context = build_metric_context(defs)
    examples = build_few_shot_examples("trading")
    messages = build_prompt("What is the total notional?", context, examples)
"""

from __future__ import annotations

SYSTEM_PROMPT = """You are a SQL expert that generates Trino SQL queries for a financial data lakehouse.

RULES:
1. Use ONLY the tables, columns, and metrics defined below. Do not invent columns or tables.
2. Financial values use DECIMAL types -- never use floating point arithmetic or FLOAT/DOUBLE casts.
3. Always qualify table names with schema: gold.table_name (e.g., gold.trading_metrics, gold.risk_exposure).
4. For aggregations, use the pre-defined metric formulas exactly as specified in the metric definitions.
5. Return ONLY valid Trino SQL. No explanations, no markdown, no commentary.

AVAILABLE METRIC DEFINITIONS:
{metric_context}

EXAMPLE QUERIES:
{few_shot_examples}"""

USER_PROMPT = """Question: {question}

Return ONLY the SQL query, no explanation."""


def build_prompt(
    question: str,
    metric_context: str,
    few_shot_examples: str,
) -> list[dict[str, str]]:
    """Build a structured message list for LLM-based NL-to-SQL generation.

    Constructs a system message with metric context and few-shot examples,
    and a user message with the natural language question.

    Args:
        question: Natural language question to convert to SQL.
        metric_context: Structured text from build_metric_context() with
            table, metric, and dimension definitions.
        few_shot_examples: Formatted Q&A pairs from build_few_shot_examples().

    Returns:
        List of message dicts with 'role' and 'content' keys, suitable
        for Claude Messages API format.
    """
    system_content = SYSTEM_PROMPT.format(
        metric_context=metric_context,
        few_shot_examples=few_shot_examples,
    )
    user_content = USER_PROMPT.format(question=question)

    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


# Domain-specific few-shot examples demonstrating expected SQL patterns.
_TRADING_EXAMPLES = """Q: What is the total notional value for AAPL?
A: SELECT SUM(total_notional) FROM gold.trading_metrics WHERE symbol = 'AAPL'

Q: How many BUY trades are there?
A: SELECT SUM(trade_count) FROM gold.trading_metrics WHERE side = 'BUY'

Q: What is the average price for each symbol?
A: SELECT symbol, AVG(avg_price) FROM gold.trading_metrics GROUP BY symbol

Q: Which symbol has the highest total notional?
A: SELECT symbol, SUM(total_notional) AS total FROM gold.trading_metrics GROUP BY symbol ORDER BY total DESC LIMIT 1

Q: Compare BUY vs SELL trade count for MSFT.
A: SELECT side, SUM(trade_count) AS trades FROM gold.trading_metrics WHERE symbol = 'MSFT' GROUP BY side"""

_RISK_EXPOSURE_EXAMPLES = """Q: What is the total market value for account ACCT-1234?
A: SELECT SUM(total_market_value) FROM gold.risk_exposure WHERE account_id = 'ACCT-1234'

Q: What is the VaR 95 for the Technology sector?
A: SELECT SUM(total_var_95) FROM gold.risk_exposure WHERE sector = 'Technology'

Q: How many positions does each account have?
A: SELECT account_id, SUM(position_count) AS positions FROM gold.risk_exposure GROUP BY account_id

Q: Which sector has the highest expected shortfall?
A: SELECT sector, SUM(total_expected_shortfall) AS es FROM gold.risk_exposure GROUP BY sector ORDER BY es DESC LIMIT 1

Q: Compare VaR 95 vs VaR 99 by currency.
A: SELECT currency, SUM(total_var_95) AS var_95, SUM(total_var_99) AS var_99 \
FROM gold.risk_exposure GROUP BY currency"""


def build_few_shot_examples(domain: str | None) -> str:
    """Return formatted few-shot Q&A pairs for a specific domain.

    Provides domain-specific example queries that demonstrate the expected
    SQL patterns, table references, and column usage for each pilot domain.

    Args:
        domain: Domain identifier ('trading', 'risk_exposure', or None).
            If None, returns an empty string (no domain-specific examples).

    Returns:
        Formatted string of Q&A pairs, or empty string if domain is None
        or unrecognized.
    """
    if domain == "trading":
        return _TRADING_EXAMPLES
    elif domain == "risk_exposure":
        return _RISK_EXPOSURE_EXAMPLES
    else:
        return ""

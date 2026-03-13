"""Data classification module for the lakehouse governance framework.

Provides tag-based sensitivity classification for columns using regex pattern matching.
Classification levels: PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED.

Tag-driven classification scales to 300+ data sources without per-column policies.
Classification tags drive Ranger tag-based masking policies (see ranger_policies.py).
"""

from __future__ import annotations

import re
from enum import Enum


class SensitivityLevel(str, Enum):
    """Sensitivity classification levels for data columns.

    Ordered from lowest to highest sensitivity:
    PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED.

    Values are strings matching Ranger tag names.
    """

    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED = "RESTRICTED"


# Classification rules: list of (regex_pattern, SensitivityLevel) tuples.
# Rules are matched case-insensitively against the column name.
# First match wins -- rules are ordered from most to least sensitive.
#
# RESTRICTED: PII and financial identifiers that are heavily regulated
# CONFIDENTIAL: Personal contact information and compensation data
# PUBLIC: Market data and non-sensitive business identifiers
CLASSIFICATION_RULES: list[tuple[str, SensitivityLevel]] = [
    # RESTRICTED: Social Security and tax identifiers
    (r"ssn", SensitivityLevel.RESTRICTED),
    (r"social.?security", SensitivityLevel.RESTRICTED),
    (r"tax.?id", SensitivityLevel.RESTRICTED),
    (r"taxpayer", SensitivityLevel.RESTRICTED),
    (r"account.?number", SensitivityLevel.RESTRICTED),
    (r"routing.?number", SensitivityLevel.RESTRICTED),
    (r"credit.?card", SensitivityLevel.RESTRICTED),
    (r"card.?number", SensitivityLevel.RESTRICTED),
    (r"bank.?account", SensitivityLevel.RESTRICTED),
    # CONFIDENTIAL: Personal contact and compensation data
    (r"email", SensitivityLevel.CONFIDENTIAL),
    (r"phone", SensitivityLevel.CONFIDENTIAL),
    (r"mobile", SensitivityLevel.CONFIDENTIAL),
    (r"address", SensitivityLevel.CONFIDENTIAL),
    (r"street", SensitivityLevel.CONFIDENTIAL),
    (r"\bcity\b", SensitivityLevel.CONFIDENTIAL),
    (r"zip", SensitivityLevel.CONFIDENTIAL),
    (r"postal", SensitivityLevel.CONFIDENTIAL),
    (r"date.?of.?birth", SensitivityLevel.CONFIDENTIAL),
    (r"\bdob\b", SensitivityLevel.CONFIDENTIAL),
    (r"salary", SensitivityLevel.CONFIDENTIAL),
    (r"compensation", SensitivityLevel.CONFIDENTIAL),
    # PUBLIC: Market and trading reference data
    (r"\bsymbol\b", SensitivityLevel.PUBLIC),
    (r"\bticker\b", SensitivityLevel.PUBLIC),
    (r"\bexchange\b", SensitivityLevel.PUBLIC),
    (r"\bcurrency\b", SensitivityLevel.PUBLIC),
    (r"\bmarket\b", SensitivityLevel.PUBLIC),
    (r"trade.?date", SensitivityLevel.PUBLIC),
    (r"report.?date", SensitivityLevel.PUBLIC),
]

# Compiled rules for performance (case-insensitive matching)
_COMPILED_RULES: list[tuple[re.Pattern[str], SensitivityLevel]] = [
    (re.compile(pattern, re.IGNORECASE), level)
    for pattern, level in CLASSIFICATION_RULES
]


def classify_column(column_name: str) -> SensitivityLevel:
    """Classify a column name to a sensitivity level using regex pattern matching.

    Matches the column name case-insensitively against CLASSIFICATION_RULES.
    Returns the sensitivity level of the first matching rule.
    Defaults to INTERNAL if no rule matches.

    Args:
        column_name: The column name to classify (e.g., "ssn", "trader_email").

    Returns:
        SensitivityLevel enum value.

    Examples:
        >>> classify_column("ssn")
        <SensitivityLevel.RESTRICTED: 'RESTRICTED'>
        >>> classify_column("trader_email")
        <SensitivityLevel.CONFIDENTIAL: 'CONFIDENTIAL'>
        >>> classify_column("symbol")
        <SensitivityLevel.PUBLIC: 'PUBLIC'>
        >>> classify_column("quantity")
        <SensitivityLevel.INTERNAL: 'INTERNAL'>
    """
    normalized = column_name.lower()
    for pattern, level in _COMPILED_RULES:
        if pattern.search(normalized):
            return level
    return SensitivityLevel.INTERNAL


def classify_table_columns(columns: list[str]) -> dict[str, SensitivityLevel]:
    """Classify a list of column names to their sensitivity levels.

    Batch operation applying classify_column() to each column name.

    Args:
        columns: List of column names to classify.

    Returns:
        Dict mapping column name to SensitivityLevel.

    Examples:
        >>> classify_table_columns(["ssn", "email", "symbol"])
        {'ssn': <SensitivityLevel.RESTRICTED: 'RESTRICTED'>, ...}
    """
    return {col: classify_column(col) for col in columns}


def get_columns_by_level(
    classified: dict[str, SensitivityLevel],
    level: SensitivityLevel,
) -> list[str]:
    """Filter classified columns to return only those at the specified sensitivity level.

    Args:
        classified: Dict mapping column name to SensitivityLevel (from classify_table_columns).
        level: The SensitivityLevel to filter by.

    Returns:
        List of column names at the specified sensitivity level.

    Examples:
        >>> cols = classify_table_columns(["ssn", "email", "symbol"])
        >>> get_columns_by_level(cols, SensitivityLevel.RESTRICTED)
        ['ssn']
    """
    return [col for col, col_level in classified.items() if col_level == level]

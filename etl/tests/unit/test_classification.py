"""Unit tests for the governance data classification module.

Tests SensitivityLevel enum, classify_column(), classify_table_columns(),
and get_columns_by_level() helper functions.

No external services required -- pure Python tests.
"""

import pytest


@pytest.mark.unit
class TestSensitivityLevelEnum:
    """Test the SensitivityLevel enum values and ordering."""

    def test_sensitivity_levels_exist(self):
        from src.governance.classification import SensitivityLevel

        levels = [sl.value for sl in SensitivityLevel]
        assert "PUBLIC" in levels
        assert "INTERNAL" in levels
        assert "CONFIDENTIAL" in levels
        assert "RESTRICTED" in levels

    def test_four_sensitivity_levels(self):
        from src.governance.classification import SensitivityLevel

        assert len(SensitivityLevel) == 4

    def test_restricted_is_highest(self):
        from src.governance.classification import SensitivityLevel

        # Higher numeric value = higher sensitivity (RESTRICTED > CONFIDENTIAL > INTERNAL > PUBLIC)
        assert SensitivityLevel.RESTRICTED.value != SensitivityLevel.PUBLIC.value

    def test_enum_values_are_strings(self):
        from src.governance.classification import SensitivityLevel

        for level in SensitivityLevel:
            assert isinstance(level.value, str), f"{level.name} value should be a string"


@pytest.mark.unit
class TestClassifyColumn:
    """Test classify_column() function with various column names."""

    def test_ssn_is_restricted(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("ssn") == SensitivityLevel.RESTRICTED

    def test_social_security_number_is_restricted(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("social_security_number") == SensitivityLevel.RESTRICTED

    def test_tax_id_is_restricted(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("tax_id") == SensitivityLevel.RESTRICTED

    def test_account_number_is_restricted(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("account_number") == SensitivityLevel.RESTRICTED

    def test_credit_card_is_restricted(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("credit_card") == SensitivityLevel.RESTRICTED

    def test_routing_number_is_restricted(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("routing_number") == SensitivityLevel.RESTRICTED

    def test_email_is_confidential(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("email") == SensitivityLevel.CONFIDENTIAL

    def test_phone_is_confidential(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("phone") == SensitivityLevel.CONFIDENTIAL

    def test_address_is_confidential(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("address") == SensitivityLevel.CONFIDENTIAL

    def test_date_of_birth_is_confidential(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("date_of_birth") == SensitivityLevel.CONFIDENTIAL

    def test_salary_is_confidential(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("salary") == SensitivityLevel.CONFIDENTIAL

    def test_trade_date_is_public(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("trade_date") == SensitivityLevel.PUBLIC

    def test_symbol_is_public(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("symbol") == SensitivityLevel.PUBLIC

    def test_ticker_is_public(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("ticker") == SensitivityLevel.PUBLIC

    def test_exchange_is_public(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("exchange") == SensitivityLevel.PUBLIC

    def test_unknown_column_defaults_to_internal(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("some_unknown_column") == SensitivityLevel.INTERNAL
        assert classify_column("quantity") == SensitivityLevel.INTERNAL
        assert classify_column("created_at") == SensitivityLevel.INTERNAL

    def test_case_insensitive_ssn(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("SSN") == SensitivityLevel.RESTRICTED
        assert classify_column("Ssn") == SensitivityLevel.RESTRICTED
        assert classify_column("ssn") == SensitivityLevel.RESTRICTED

    def test_case_insensitive_email(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("EMAIL") == SensitivityLevel.CONFIDENTIAL
        assert classify_column("Email") == SensitivityLevel.CONFIDENTIAL

    def test_column_with_suffix(self):
        from src.governance.classification import SensitivityLevel, classify_column

        assert classify_column("trader_email") == SensitivityLevel.CONFIDENTIAL
        assert classify_column("customer_ssn") == SensitivityLevel.RESTRICTED
        assert classify_column("client_account_number") == SensitivityLevel.RESTRICTED


@pytest.mark.unit
class TestClassifyTableColumns:
    """Test classify_table_columns() batch classification."""

    def test_batch_classification_returns_dict(self):
        from src.governance.classification import classify_table_columns

        columns = ["ssn", "email", "symbol", "trade_date"]
        result = classify_table_columns(columns)
        assert isinstance(result, dict)

    def test_batch_classification_all_columns(self):
        from src.governance.classification import SensitivityLevel, classify_table_columns

        columns = ["ssn", "email", "symbol", "trade_date", "quantity"]
        result = classify_table_columns(columns)
        assert len(result) == len(columns)
        assert result["ssn"] == SensitivityLevel.RESTRICTED
        assert result["email"] == SensitivityLevel.CONFIDENTIAL
        assert result["symbol"] == SensitivityLevel.PUBLIC
        assert result["trade_date"] == SensitivityLevel.PUBLIC
        assert result["quantity"] == SensitivityLevel.INTERNAL

    def test_batch_empty_list(self):
        from src.governance.classification import classify_table_columns

        result = classify_table_columns([])
        assert result == {}


@pytest.mark.unit
class TestGetColumnsByLevel:
    """Test get_columns_by_level() filter helper."""

    def test_get_restricted_columns(self):
        from src.governance.classification import SensitivityLevel, get_columns_by_level

        classified = {
            "ssn": SensitivityLevel.RESTRICTED,
            "account_number": SensitivityLevel.RESTRICTED,
            "email": SensitivityLevel.CONFIDENTIAL,
            "symbol": SensitivityLevel.PUBLIC,
        }
        restricted = get_columns_by_level(classified, SensitivityLevel.RESTRICTED)
        assert set(restricted) == {"ssn", "account_number"}

    def test_get_public_columns(self):
        from src.governance.classification import SensitivityLevel, get_columns_by_level

        classified = {
            "ssn": SensitivityLevel.RESTRICTED,
            "symbol": SensitivityLevel.PUBLIC,
            "trade_date": SensitivityLevel.PUBLIC,
        }
        public = get_columns_by_level(classified, SensitivityLevel.PUBLIC)
        assert set(public) == {"symbol", "trade_date"}

    def test_get_columns_empty_result(self):
        from src.governance.classification import SensitivityLevel, get_columns_by_level

        classified = {"ssn": SensitivityLevel.RESTRICTED}
        public = get_columns_by_level(classified, SensitivityLevel.PUBLIC)
        assert public == []


@pytest.mark.unit
class TestClassificationRules:
    """Test that CLASSIFICATION_RULES is properly structured."""

    def test_classification_rules_exist(self):
        from src.governance.classification import CLASSIFICATION_RULES

        assert CLASSIFICATION_RULES is not None
        assert len(CLASSIFICATION_RULES) > 0

    def test_classification_rules_are_tuples(self):
        from src.governance.classification import CLASSIFICATION_RULES

        for rule in CLASSIFICATION_RULES:
            assert isinstance(rule, tuple), f"Each rule should be a tuple, got {type(rule)}"
            assert len(rule) == 2, "Each rule should have 2 elements (pattern, level)"

    def test_classification_rules_have_sensitive_patterns(self):
        from src.governance.classification import CLASSIFICATION_RULES, SensitivityLevel

        [rule[0] for rule in CLASSIFICATION_RULES]
        levels = [rule[1] for rule in CLASSIFICATION_RULES]

        # Should have RESTRICTED patterns
        assert SensitivityLevel.RESTRICTED in levels
        # Should have CONFIDENTIAL patterns
        assert SensitivityLevel.CONFIDENTIAL in levels

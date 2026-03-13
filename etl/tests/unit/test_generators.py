"""Unit tests for synthetic financial data generators.

Tests cover:
- generate_trades: correct record counts, field names, determinism, Decimal types
- generate_positions: correct record counts, field names, determinism, Decimal types
- generate_risk_metrics: correct record counts, field names, determinism, Decimal types
"""

from decimal import Decimal


class TestGenerateTrades:
    """Tests for generate_trades function."""

    def test_returns_correct_count(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(100)
        assert len(result) == 100

    def test_returns_correct_count_small(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(5)
        assert len(result) == 5

    def test_returns_list_of_dicts(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(10)
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    def test_has_required_fields(self):
        from src.synthetic.generators import generate_trades

        required_fields = {
            "trade_id",
            "trade_date",
            "symbol",
            "side",
            "trade_type",
            "quantity",
            "price",
            "notional",
            "account_id",
            "trader_id",
            "exchange",
            "settlement_date",
        }
        result = generate_trades(10)
        for record in result:
            assert set(record.keys()) == required_fields, f"Missing fields: {required_fields - set(record.keys())}"

    def test_deterministic_with_same_seed(self):
        from src.synthetic.generators import generate_trades

        result1 = generate_trades(50, seed=42)
        result2 = generate_trades(50, seed=42)
        assert result1 == result2

    def test_different_seeds_produce_different_data(self):
        from src.synthetic.generators import generate_trades

        result1 = generate_trades(50, seed=42)
        result2 = generate_trades(50, seed=99)
        assert result1 != result2

    def test_price_is_decimal(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(10)
        for record in result:
            assert isinstance(record["price"], Decimal), f"price should be Decimal, got {type(record['price'])}"

    def test_notional_is_decimal(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(10)
        for record in result:
            assert isinstance(record["notional"], Decimal), f"notional should be Decimal, got {type(record['notional'])}"

    def test_valid_side_values(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(100)
        valid_sides = {"BUY", "SELL"}
        for record in result:
            assert record["side"] in valid_sides, f"Invalid side: {record['side']}"

    def test_valid_trade_type_values(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(100)
        valid_types = {"MARKET", "LIMIT", "STOP", "STOP_LIMIT"}
        for record in result:
            assert record["trade_type"] in valid_types, f"Invalid trade type: {record['trade_type']}"

    def test_valid_exchange_values(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(100)
        valid_exchanges = {"NYSE", "NASDAQ", "LSE", "TSE"}
        for record in result:
            assert record["exchange"] in valid_exchanges, f"Invalid exchange: {record['exchange']}"

    def test_valid_symbol_values(self):
        from src.synthetic.generators import generate_trades

        result = generate_trades(100)
        valid_symbols = {
            "AAPL", "GOOGL", "MSFT", "JPM", "GS", "BAC", "C", "WFC",
            "BRK.B", "V", "MA", "AXP", "BLK", "SCHW", "MS",
        }
        for record in result:
            assert record["symbol"] in valid_symbols, f"Invalid symbol: {record['symbol']}"


class TestGeneratePositions:
    """Tests for generate_positions function."""

    def test_returns_correct_count(self):
        from src.synthetic.generators import generate_positions

        result = generate_positions(50)
        assert len(result) == 50

    def test_returns_list_of_dicts(self):
        from src.synthetic.generators import generate_positions

        result = generate_positions(10)
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    def test_has_required_fields(self):
        from src.synthetic.generators import generate_positions

        required_fields = {
            "position_id",
            "account_id",
            "symbol",
            "quantity",
            "market_value",
            "as_of_date",
            "sector",
            "currency",
        }
        result = generate_positions(10)
        for record in result:
            assert set(record.keys()) == required_fields, f"Missing fields: {required_fields - set(record.keys())}"

    def test_deterministic_with_same_seed(self):
        from src.synthetic.generators import generate_positions

        result1 = generate_positions(50, seed=42)
        result2 = generate_positions(50, seed=42)
        assert result1 == result2

    def test_different_seeds_produce_different_data(self):
        from src.synthetic.generators import generate_positions

        result1 = generate_positions(50, seed=42)
        result2 = generate_positions(50, seed=99)
        assert result1 != result2

    def test_market_value_is_decimal(self):
        from src.synthetic.generators import generate_positions

        result = generate_positions(10)
        for record in result:
            assert isinstance(
                record["market_value"], Decimal
            ), f"market_value should be Decimal, got {type(record['market_value'])}"


class TestGenerateRiskMetrics:
    """Tests for generate_risk_metrics function."""

    def test_returns_correct_count(self):
        from src.synthetic.generators import generate_risk_metrics

        result = generate_risk_metrics(30)
        assert len(result) == 30

    def test_returns_list_of_dicts(self):
        from src.synthetic.generators import generate_risk_metrics

        result = generate_risk_metrics(10)
        assert isinstance(result, list)
        assert all(isinstance(r, dict) for r in result)

    def test_has_required_fields(self):
        from src.synthetic.generators import generate_risk_metrics

        required_fields = {
            "metric_id",
            "account_id",
            "var_95",
            "var_99",
            "expected_shortfall",
            "stress_pnl",
            "calc_date",
            "model_version",
        }
        result = generate_risk_metrics(10)
        for record in result:
            assert set(record.keys()) == required_fields, f"Missing fields: {required_fields - set(record.keys())}"

    def test_deterministic_with_same_seed(self):
        from src.synthetic.generators import generate_risk_metrics

        result1 = generate_risk_metrics(30, seed=42)
        result2 = generate_risk_metrics(30, seed=42)
        assert result1 == result2

    def test_different_seeds_produce_different_data(self):
        from src.synthetic.generators import generate_risk_metrics

        result1 = generate_risk_metrics(30, seed=42)
        result2 = generate_risk_metrics(30, seed=99)
        assert result1 != result2

    def test_var_fields_are_decimal(self):
        from src.synthetic.generators import generate_risk_metrics

        result = generate_risk_metrics(10)
        for record in result:
            assert isinstance(record["var_95"], Decimal), f"var_95 should be Decimal, got {type(record['var_95'])}"
            assert isinstance(record["var_99"], Decimal), f"var_99 should be Decimal, got {type(record['var_99'])}"

    def test_expected_shortfall_is_decimal(self):
        from src.synthetic.generators import generate_risk_metrics

        result = generate_risk_metrics(10)
        for record in result:
            assert isinstance(
                record["expected_shortfall"], Decimal
            ), f"expected_shortfall should be Decimal, got {type(record['expected_shortfall'])}"

    def test_stress_pnl_is_decimal(self):
        from src.synthetic.generators import generate_risk_metrics

        result = generate_risk_metrics(10)
        for record in result:
            assert isinstance(
                record["stress_pnl"], Decimal
            ), f"stress_pnl should be Decimal, got {type(record['stress_pnl'])}"

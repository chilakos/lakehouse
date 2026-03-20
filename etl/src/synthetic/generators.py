"""Deterministic synthetic financial data generators for lakehouse testing.

Provides generators for trades, positions, and risk metrics with:
- Fixed seed for reproducible output
- Decimal types for financial precision
- Realistic field values (symbols, exchanges, sectors)
- PySpark StructType schemas for Iceberg table creation
"""

import random
from datetime import date, timedelta
from decimal import Decimal

from faker import Faker

# Financial reference data
SYMBOLS = [
    "AAPL",
    "GOOGL",
    "MSFT",
    "JPM",
    "GS",
    "BAC",
    "C",
    "WFC",
    "BRK.B",
    "V",
    "MA",
    "AXP",
    "BLK",
    "SCHW",
    "MS",
]

SIDES = ["BUY", "SELL"]

TRADE_TYPES = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]

EXCHANGES = ["NYSE", "NASDAQ", "LSE", "TSE"]

SECTORS = [
    "Technology",
    "Financial Services",
    "Healthcare",
    "Consumer Discretionary",
    "Industrials",
    "Energy",
    "Materials",
    "Utilities",
    "Real Estate",
    "Communication Services",
]

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF"]

MODEL_VERSIONS = ["v1.0", "v1.1", "v2.0", "v2.1", "v3.0"]


def generate_trades(num_records: int, seed: int = 42) -> list[dict]:
    """Generate deterministic synthetic trade records.

    Args:
        num_records: Number of trade records to generate.
        seed: Random seed for deterministic output.

    Returns:
        List of trade dictionaries with financial precision (Decimal types).
    """
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)

    trades = []
    for i in range(num_records):
        symbol = rng.choice(SYMBOLS)
        price = round(rng.uniform(50.0, 500.0), 4)
        quantity = rng.randint(1, 10000)
        trade_date = fake.date_between(
            start_date=date(2024, 1, 1),
            end_date=date(2026, 3, 13),
        )
        trades.append(
            {
                "trade_id": i + 1,
                "trade_date": trade_date,
                "symbol": symbol,
                "side": rng.choice(SIDES),
                "trade_type": rng.choice(TRADE_TYPES),
                "quantity": quantity,
                "price": Decimal(str(price)),
                "notional": Decimal(str(round(price * quantity, 4))),
                "account_id": f"ACCT-{rng.randint(1000, 9999)}",
                "trader_id": f"TRD-{rng.randint(100, 999)}",
                "exchange": rng.choice(EXCHANGES),
                "settlement_date": trade_date + timedelta(days=rng.choice([1, 2, 3])),
            }
        )
    return trades


def generate_positions(num_records: int, seed: int = 42) -> list[dict]:
    """Generate deterministic synthetic portfolio position records.

    Args:
        num_records: Number of position records to generate.
        seed: Random seed for deterministic output.

    Returns:
        List of position dictionaries with financial precision (Decimal types).
    """
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)

    positions = []
    for i in range(num_records):
        quantity = rng.randint(100, 100000)
        price_per_unit = round(rng.uniform(10.0, 1000.0), 4)
        positions.append(
            {
                "position_id": i + 1,
                "account_id": f"ACCT-{rng.randint(1000, 9999)}",
                "symbol": rng.choice(SYMBOLS),
                "quantity": quantity,
                "market_value": Decimal(str(round(price_per_unit * quantity, 4))),
                "as_of_date": fake.date_between(
                    start_date=date(2024, 1, 1),
                    end_date=date(2026, 3, 13),
                ),
                "sector": rng.choice(SECTORS),
                "currency": rng.choice(CURRENCIES),
            }
        )
    return positions


def generate_risk_metrics(num_records: int, seed: int = 42) -> list[dict]:
    """Generate deterministic synthetic risk metric records.

    Args:
        num_records: Number of risk metric records to generate.
        seed: Random seed for deterministic output.

    Returns:
        List of risk metric dictionaries with financial precision (Decimal types).
    """
    fake = Faker()
    Faker.seed(seed)
    rng = random.Random(seed)

    metrics = []
    for i in range(num_records):
        # VaR 99 is always larger than VaR 95 (more extreme tail risk)
        var_95 = round(rng.uniform(10000.0, 500000.0), 2)
        var_99 = round(var_95 * rng.uniform(1.2, 1.8), 2)
        expected_shortfall = round(var_99 * rng.uniform(1.1, 1.5), 2)
        stress_pnl = round(rng.uniform(-2000000.0, -100000.0), 2)

        metrics.append(
            {
                "metric_id": i + 1,
                "account_id": f"ACCT-{rng.randint(1000, 9999)}",
                "var_95": Decimal(str(var_95)),
                "var_99": Decimal(str(var_99)),
                "expected_shortfall": Decimal(str(expected_shortfall)),
                "stress_pnl": Decimal(str(stress_pnl)),
                "calc_date": fake.date_between(
                    start_date=date(2024, 1, 1),
                    end_date=date(2026, 3, 13),
                ),
                "model_version": rng.choice(MODEL_VERSIONS),
            }
        )
    return metrics


def trades_schema():
    """Return PySpark StructType schema for the trades table.

    Returns:
        PySpark StructType defining the trades table schema.
    """
    from pyspark.sql.types import (
        DateType,
        DecimalType,
        IntegerType,
        StringType,
        StructField,
        StructType,
    )

    return StructType(
        [
            StructField("trade_id", IntegerType(), nullable=False),
            StructField("trade_date", DateType(), nullable=False),
            StructField("symbol", StringType(), nullable=False),
            StructField("side", StringType(), nullable=False),
            StructField("trade_type", StringType(), nullable=False),
            StructField("quantity", IntegerType(), nullable=False),
            StructField("price", DecimalType(18, 4), nullable=False),
            StructField("notional", DecimalType(18, 4), nullable=False),
            StructField("account_id", StringType(), nullable=False),
            StructField("trader_id", StringType(), nullable=False),
            StructField("exchange", StringType(), nullable=False),
            StructField("settlement_date", DateType(), nullable=False),
        ]
    )


def positions_schema():
    """Return PySpark StructType schema for the positions table.

    Returns:
        PySpark StructType defining the positions table schema.
    """
    from pyspark.sql.types import (
        DateType,
        DecimalType,
        IntegerType,
        StringType,
        StructField,
        StructType,
    )

    return StructType(
        [
            StructField("position_id", IntegerType(), nullable=False),
            StructField("account_id", StringType(), nullable=False),
            StructField("symbol", StringType(), nullable=False),
            StructField("quantity", IntegerType(), nullable=False),
            StructField("market_value", DecimalType(18, 4), nullable=False),
            StructField("as_of_date", DateType(), nullable=False),
            StructField("sector", StringType(), nullable=False),
            StructField("currency", StringType(), nullable=False),
        ]
    )


def risk_metrics_schema():
    """Return PySpark StructType schema for the risk metrics table.

    Returns:
        PySpark StructType defining the risk metrics table schema.
    """
    from pyspark.sql.types import (
        DateType,
        DecimalType,
        IntegerType,
        StringType,
        StructField,
        StructType,
    )

    return StructType(
        [
            StructField("metric_id", IntegerType(), nullable=False),
            StructField("account_id", StringType(), nullable=False),
            StructField("var_95", DecimalType(18, 2), nullable=False),
            StructField("var_99", DecimalType(18, 2), nullable=False),
            StructField("expected_shortfall", DecimalType(18, 2), nullable=False),
            StructField("stress_pnl", DecimalType(18, 2), nullable=False),
            StructField("calc_date", DateType(), nullable=False),
            StructField("model_version", StringType(), nullable=False),
        ]
    )

"""Synthetic data generation for lakehouse testing.

Provides deterministic generators for financial data:
- generate_trades: Trade records with symbol, price, quantity, exchange
- generate_positions: Portfolio positions with market value, sector
- generate_risk_metrics: VaR, expected shortfall, stress P&L
"""

from src.synthetic.generators import (
    generate_positions,
    generate_risk_metrics,
    generate_trades,
    positions_schema,
    risk_metrics_schema,
    trades_schema,
)

__all__ = [
    "generate_trades",
    "generate_positions",
    "generate_risk_metrics",
    "trades_schema",
    "positions_schema",
    "risk_metrics_schema",
]

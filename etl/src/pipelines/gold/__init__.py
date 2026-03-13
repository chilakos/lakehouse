"""Gold layer pipeline implementations.

Gold = pre-aggregated metrics for BI AND curated entity views for
specific consumers (regulatory reports, trading desk views).
"""

from src.pipelines.gold.risk_exposure import RiskExposureGoldPipeline
from src.pipelines.gold.trading_metrics import TradingMetricsGoldPipeline

__all__ = [
    "RiskExposureGoldPipeline",
    "TradingMetricsGoldPipeline",
]

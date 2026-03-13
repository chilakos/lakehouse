"""Data freshness SLA tracking with traffic-light status.

Provides per-table freshness monitoring with GREEN/YELLOW/RED status
based on configurable SLA thresholds per medallion layer.

Usage::

    from src.governance.freshness_tracker import (
        check_table_freshness,
        get_freshness_badge,
        FreshnessSLA,
        FreshnessStatus,
        DEFAULT_SLAS,
    )

    sla = DEFAULT_SLAS["gold.*"]
    last_updated = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    status = check_table_freshness(last_updated, sla)
    badge = get_freshness_badge(status)
    # {"status": "green", "label": "On time", "icon": "check-circle"}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class FreshnessStatus(Enum):
    """Traffic-light status for data freshness SLA compliance.

    Values:
        GREEN: Data is current -- within expected update interval (and grace period up to warning threshold).
        YELLOW: Data is stale -- past warning threshold but within critical threshold.
        RED: Data is critically stale -- past critical threshold, or never updated.
    """

    GREEN = "On time"
    YELLOW = "Warning"
    RED = "Stale"


@dataclass
class FreshnessSLA:
    """Service Level Agreement for data freshness per table.

    Attributes:
        table_name: Fully qualified table name (e.g., "gold.positions_daily")
        expected_update_interval_hours: Normal expected update cadence in hours.
            Data within this window (plus grace to warning threshold) is GREEN.
        warning_threshold_hours: Hours after which status becomes YELLOW.
            Must be >= expected_update_interval_hours.
        critical_threshold_hours: Hours after which status becomes RED.
            Must be >= warning_threshold_hours.

    Example::

        sla = FreshnessSLA(
            table_name="gold.trades_daily",
            expected_update_interval_hours=24.0,
            warning_threshold_hours=26.0,
            critical_threshold_hours=48.0,
        )
    """

    table_name: str
    expected_update_interval_hours: float
    warning_threshold_hours: float
    critical_threshold_hours: float


# Default SLAs by medallion layer pattern.
# Keys are regex-style pattern strings; use to look up SLA by table prefix.
DEFAULT_SLAS: dict[str, FreshnessSLA] = {
    "gold.*": FreshnessSLA(
        table_name="gold.*",
        expected_update_interval_hours=24.0,
        warning_threshold_hours=26.0,
        critical_threshold_hours=48.0,
    ),
    "silver.*": FreshnessSLA(
        table_name="silver.*",
        expected_update_interval_hours=12.0,
        warning_threshold_hours=14.0,
        critical_threshold_hours=24.0,
    ),
    "bronze.*": FreshnessSLA(
        table_name="bronze.*",
        expected_update_interval_hours=6.0,
        warning_threshold_hours=8.0,
        critical_threshold_hours=12.0,
    ),
}

# Traffic-light badge metadata keyed by FreshnessStatus
_BADGE_MAP: dict[FreshnessStatus, dict] = {
    FreshnessStatus.GREEN: {
        "status": "green",
        "label": "On time",
        "icon": "check-circle",
    },
    FreshnessStatus.YELLOW: {
        "status": "yellow",
        "label": "Warning",
        "icon": "exclamation-triangle",
    },
    FreshnessStatus.RED: {
        "status": "red",
        "label": "Stale",
        "icon": "x-circle",
    },
}


def check_table_freshness(
    last_updated: Optional[datetime],
    sla: FreshnessSLA,
) -> FreshnessStatus:
    """Check data freshness status for a single table against its SLA.

    Args:
        last_updated: UTC datetime of last successful data update.
            Pass ``None`` if the table has never been updated.
        sla: FreshnessSLA defining expected/warning/critical thresholds.

    Returns:
        FreshnessStatus: GREEN if current, YELLOW if warning, RED if stale.

    SLA logic::

        hours_since <= warning_threshold  =>  GREEN
        hours_since <= critical_threshold =>  YELLOW
        hours_since >  critical_threshold =>  RED
        last_updated is None              =>  RED (never updated)
    """
    if last_updated is None:
        logger.warning(
            "Table %s has no last_updated timestamp -- marking RED (never updated)",
            sla.table_name,
        )
        return FreshnessStatus.RED

    now = datetime.now(timezone.utc)

    # Normalise naive datetimes to UTC
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=timezone.utc)

    hours_since = (now - last_updated).total_seconds() / 3600.0

    if hours_since <= sla.warning_threshold_hours:
        return FreshnessStatus.GREEN
    elif hours_since <= sla.critical_threshold_hours:
        return FreshnessStatus.YELLOW
    else:
        return FreshnessStatus.RED


def get_freshness_badge(status: FreshnessStatus) -> dict:
    """Return traffic-light UI metadata for a freshness status.

    Args:
        status: FreshnessStatus enum value.

    Returns:
        dict with keys:
            - ``status``: CSS colour string ("green", "yellow", "red")
            - ``label``: Human-readable label ("On time", "Warning", "Stale")
            - ``icon``: Icon identifier for UI components
    """
    return dict(_BADGE_MAP[status])


def get_all_freshness(
    table_slas: dict[str, FreshnessSLA],
    last_updated_map: dict[str, Optional[datetime]],
) -> list[dict]:
    """Batch freshness check for multiple tables.

    Args:
        table_slas: Mapping from table name to its FreshnessSLA.
        last_updated_map: Mapping from table name to last update datetime.
            Tables not present in this map are treated as never-updated (RED).

    Returns:
        List of dicts, one per table, each containing:
            - ``table``: Table name
            - ``status``: FreshnessStatus enum value
            - ``hours_since_update``: Float hours since last update (None if never updated)
            - ``sla_hours``: Expected update interval in hours from the SLA
            - ``badge``: Result of get_freshness_badge() for this status
    """
    results = []
    now = datetime.now(timezone.utc)

    for table_name, sla in table_slas.items():
        last_updated = last_updated_map.get(table_name)
        status = check_table_freshness(last_updated, sla)

        hours_since: Optional[float] = None
        if last_updated is not None:
            ts = last_updated
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            hours_since = (now - ts).total_seconds() / 3600.0

        results.append(
            {
                "table": table_name,
                "status": status,
                "hours_since_update": hours_since,
                "sla_hours": sla.expected_update_interval_hours,
                "badge": get_freshness_badge(status),
            }
        )

    return results

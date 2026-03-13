"""Unit tests for the data freshness tracker module.

Tests SLA-based traffic-light status (GREEN/YELLOW/RED) for
bronze, silver, and gold layer tables.

No external services required -- pure Python unit tests.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.governance.freshness_tracker import (
    DEFAULT_SLAS,
    FreshnessSLA,
    FreshnessStatus,
    check_table_freshness,
    get_all_freshness,
    get_freshness_badge,
)


@pytest.mark.unit
class TestFreshnessStatusEnum:
    """Test that FreshnessStatus enum has correct values."""

    def test_green_status_exists(self):
        assert FreshnessStatus.GREEN is not None

    def test_yellow_status_exists(self):
        assert FreshnessStatus.YELLOW is not None

    def test_red_status_exists(self):
        assert FreshnessStatus.RED is not None

    def test_green_value(self):
        assert FreshnessStatus.GREEN.value == "On time"

    def test_yellow_value(self):
        assert FreshnessStatus.YELLOW.value == "Warning"

    def test_red_value(self):
        assert FreshnessStatus.RED.value == "Stale"

    def test_status_enum_has_three_members(self):
        members = list(FreshnessStatus)
        assert len(members) == 3, f"FreshnessStatus should have 3 members, got {len(members)}"


@pytest.mark.unit
class TestFreshnessSLADataclass:
    """Test FreshnessSLA dataclass structure and defaults."""

    def test_create_sla_with_required_fields(self):
        sla = FreshnessSLA(
            table_name="gold.trades_daily",
            expected_update_interval_hours=24.0,
            warning_threshold_hours=26.0,
            critical_threshold_hours=48.0,
        )
        assert sla.table_name == "gold.trades_daily"
        assert sla.expected_update_interval_hours == 24.0
        assert sla.warning_threshold_hours == 26.0
        assert sla.critical_threshold_hours == 48.0

    def test_sla_is_dataclass(self):
        import dataclasses
        assert dataclasses.is_dataclass(FreshnessSLA)

    def test_sla_table_name_is_str(self):
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(FreshnessSLA)}
        assert "table_name" in fields

    def test_sla_expected_interval_field_exists(self):
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(FreshnessSLA)}
        assert "expected_update_interval_hours" in fields

    def test_sla_warning_threshold_field_exists(self):
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(FreshnessSLA)}
        assert "warning_threshold_hours" in fields

    def test_sla_critical_threshold_field_exists(self):
        import dataclasses
        fields = {f.name: f for f in dataclasses.fields(FreshnessSLA)}
        assert "critical_threshold_hours" in fields


@pytest.mark.unit
class TestCheckTableFreshness:
    """Test check_table_freshness returns correct SLA status."""

    @pytest.fixture
    def gold_sla(self):
        return FreshnessSLA(
            table_name="gold.positions",
            expected_update_interval_hours=24.0,
            warning_threshold_hours=26.0,
            critical_threshold_hours=48.0,
        )

    def test_within_expected_interval_returns_green(self, gold_sla):
        # 12 hours ago -- well within 24h expected interval
        last_updated = datetime.now(timezone.utc) - timedelta(hours=12)
        status = check_table_freshness(last_updated, gold_sla)
        assert status == FreshnessStatus.GREEN

    def test_exactly_at_expected_interval_returns_green(self, gold_sla):
        # Exactly 24 hours ago -- at the boundary
        last_updated = datetime.now(timezone.utc) - timedelta(hours=24)
        status = check_table_freshness(last_updated, gold_sla)
        assert status == FreshnessStatus.GREEN

    def test_past_expected_but_within_warning_returns_green(self, gold_sla):
        # 25 hours ago -- past expected (24h) but within warning threshold (26h)
        last_updated = datetime.now(timezone.utc) - timedelta(hours=25)
        status = check_table_freshness(last_updated, gold_sla)
        assert status == FreshnessStatus.GREEN

    def test_past_warning_threshold_returns_yellow(self, gold_sla):
        # 30 hours ago -- past warning (26h) but within critical (48h)
        last_updated = datetime.now(timezone.utc) - timedelta(hours=30)
        status = check_table_freshness(last_updated, gold_sla)
        assert status == FreshnessStatus.YELLOW

    def test_at_critical_threshold_returns_red(self, gold_sla):
        # Exactly 48 hours ago -- at critical threshold
        last_updated = datetime.now(timezone.utc) - timedelta(hours=48)
        status = check_table_freshness(last_updated, gold_sla)
        assert status == FreshnessStatus.RED

    def test_past_critical_threshold_returns_red(self, gold_sla):
        # 72 hours ago -- well past critical threshold
        last_updated = datetime.now(timezone.utc) - timedelta(hours=72)
        status = check_table_freshness(last_updated, gold_sla)
        assert status == FreshnessStatus.RED

    def test_none_last_updated_returns_red(self, gold_sla):
        # Never updated -- should be RED
        status = check_table_freshness(None, gold_sla)
        assert status == FreshnessStatus.RED

    def test_silver_sla_within_expected_returns_green(self):
        silver_sla = FreshnessSLA(
            table_name="silver.trades",
            expected_update_interval_hours=12.0,
            warning_threshold_hours=14.0,
            critical_threshold_hours=24.0,
        )
        last_updated = datetime.now(timezone.utc) - timedelta(hours=6)
        status = check_table_freshness(last_updated, silver_sla)
        assert status == FreshnessStatus.GREEN

    def test_bronze_sla_stale_returns_red(self):
        bronze_sla = FreshnessSLA(
            table_name="bronze.raw_trades",
            expected_update_interval_hours=6.0,
            warning_threshold_hours=8.0,
            critical_threshold_hours=12.0,
        )
        last_updated = datetime.now(timezone.utc) - timedelta(hours=15)
        status = check_table_freshness(last_updated, bronze_sla)
        assert status == FreshnessStatus.RED

    def test_naive_datetime_handled(self, gold_sla):
        # Naive datetime (no timezone) should be handled gracefully
        last_updated = datetime.utcnow() - timedelta(hours=5)
        # Should not raise an exception -- implementation can treat as UTC
        status = check_table_freshness(last_updated, gold_sla)
        assert status in list(FreshnessStatus)


@pytest.mark.unit
class TestGetFreshnessBadge:
    """Test get_freshness_badge returns correct traffic-light UI metadata."""

    def test_green_badge_has_status_green(self):
        badge = get_freshness_badge(FreshnessStatus.GREEN)
        assert badge["status"] == "green"

    def test_yellow_badge_has_status_yellow(self):
        badge = get_freshness_badge(FreshnessStatus.YELLOW)
        assert badge["status"] == "yellow"

    def test_red_badge_has_status_red(self):
        badge = get_freshness_badge(FreshnessStatus.RED)
        assert badge["status"] == "red"

    def test_green_badge_has_label(self):
        badge = get_freshness_badge(FreshnessStatus.GREEN)
        assert "label" in badge
        assert badge["label"]  # non-empty

    def test_yellow_badge_has_label(self):
        badge = get_freshness_badge(FreshnessStatus.YELLOW)
        assert "label" in badge
        assert badge["label"]

    def test_red_badge_has_label(self):
        badge = get_freshness_badge(FreshnessStatus.RED)
        assert "label" in badge
        assert badge["label"]

    def test_green_badge_has_icon(self):
        badge = get_freshness_badge(FreshnessStatus.GREEN)
        assert "icon" in badge
        assert badge["icon"]

    def test_yellow_badge_has_icon(self):
        badge = get_freshness_badge(FreshnessStatus.YELLOW)
        assert "icon" in badge
        assert badge["icon"]

    def test_red_badge_has_icon(self):
        badge = get_freshness_badge(FreshnessStatus.RED)
        assert "icon" in badge
        assert badge["icon"]

    def test_badge_returns_dict(self):
        badge = get_freshness_badge(FreshnessStatus.GREEN)
        assert isinstance(badge, dict)


@pytest.mark.unit
class TestDefaultSLAs:
    """Test DEFAULT_SLAS covers gold, silver, and bronze patterns."""

    def test_default_slas_is_dict(self):
        assert isinstance(DEFAULT_SLAS, dict)

    def test_gold_pattern_in_default_slas(self):
        assert any("gold" in key for key in DEFAULT_SLAS.keys()), (
            "DEFAULT_SLAS should have a key matching gold tables"
        )

    def test_silver_pattern_in_default_slas(self):
        assert any("silver" in key for key in DEFAULT_SLAS.keys()), (
            "DEFAULT_SLAS should have a key matching silver tables"
        )

    def test_bronze_pattern_in_default_slas(self):
        assert any("bronze" in key for key in DEFAULT_SLAS.keys()), (
            "DEFAULT_SLAS should have a key matching bronze tables"
        )

    def test_gold_sla_has_24h_expected(self):
        gold_key = next(k for k in DEFAULT_SLAS if "gold" in k)
        sla = DEFAULT_SLAS[gold_key]
        assert sla.expected_update_interval_hours == 24.0, (
            "Gold SLA should have 24h expected update interval"
        )

    def test_silver_sla_has_12h_expected(self):
        silver_key = next(k for k in DEFAULT_SLAS if "silver" in k)
        sla = DEFAULT_SLAS[silver_key]
        assert sla.expected_update_interval_hours == 12.0, (
            "Silver SLA should have 12h expected update interval"
        )

    def test_bronze_sla_has_6h_expected(self):
        bronze_key = next(k for k in DEFAULT_SLAS if "bronze" in k)
        sla = DEFAULT_SLAS[bronze_key]
        assert sla.expected_update_interval_hours == 6.0, (
            "Bronze SLA should have 6h expected update interval"
        )

    def test_gold_critical_is_48h(self):
        gold_key = next(k for k in DEFAULT_SLAS if "gold" in k)
        sla = DEFAULT_SLAS[gold_key]
        assert sla.critical_threshold_hours == 48.0, (
            "Gold SLA critical threshold should be 48h"
        )

    def test_silver_critical_is_24h(self):
        silver_key = next(k for k in DEFAULT_SLAS if "silver" in k)
        sla = DEFAULT_SLAS[silver_key]
        assert sla.critical_threshold_hours == 24.0, (
            "Silver SLA critical threshold should be 24h"
        )

    def test_bronze_critical_is_12h(self):
        bronze_key = next(k for k in DEFAULT_SLAS if "bronze" in k)
        sla = DEFAULT_SLAS[bronze_key]
        assert sla.critical_threshold_hours == 12.0, (
            "Bronze SLA critical threshold should be 12h"
        )


@pytest.mark.unit
class TestGetAllFreshness:
    """Test get_all_freshness batch freshness check."""

    def test_returns_list(self):
        sla = FreshnessSLA(
            table_name="gold.test",
            expected_update_interval_hours=24.0,
            warning_threshold_hours=26.0,
            critical_threshold_hours=48.0,
        )
        now = datetime.now(timezone.utc)
        result = get_all_freshness(
            table_slas={"gold.test": sla},
            last_updated_map={"gold.test": now - timedelta(hours=1)},
        )
        assert isinstance(result, list)

    def test_returns_one_entry_per_table(self):
        slas = {
            "gold.trades": FreshnessSLA("gold.trades", 24.0, 26.0, 48.0),
            "silver.positions": FreshnessSLA("silver.positions", 12.0, 14.0, 24.0),
        }
        now = datetime.now(timezone.utc)
        last_updated = {
            "gold.trades": now - timedelta(hours=1),
            "silver.positions": now - timedelta(hours=2),
        }
        result = get_all_freshness(table_slas=slas, last_updated_map=last_updated)
        assert len(result) == 2

    def test_each_entry_has_table_field(self):
        sla = FreshnessSLA("gold.test", 24.0, 26.0, 48.0)
        now = datetime.now(timezone.utc)
        result = get_all_freshness(
            table_slas={"gold.test": sla},
            last_updated_map={"gold.test": now - timedelta(hours=1)},
        )
        assert "table" in result[0]

    def test_each_entry_has_status_field(self):
        sla = FreshnessSLA("gold.test", 24.0, 26.0, 48.0)
        now = datetime.now(timezone.utc)
        result = get_all_freshness(
            table_slas={"gold.test": sla},
            last_updated_map={"gold.test": now - timedelta(hours=1)},
        )
        assert "status" in result[0]

    def test_each_entry_has_hours_since_update_field(self):
        sla = FreshnessSLA("gold.test", 24.0, 26.0, 48.0)
        now = datetime.now(timezone.utc)
        result = get_all_freshness(
            table_slas={"gold.test": sla},
            last_updated_map={"gold.test": now - timedelta(hours=5)},
        )
        assert "hours_since_update" in result[0]

    def test_each_entry_has_sla_hours_field(self):
        sla = FreshnessSLA("gold.test", 24.0, 26.0, 48.0)
        now = datetime.now(timezone.utc)
        result = get_all_freshness(
            table_slas={"gold.test": sla},
            last_updated_map={"gold.test": now - timedelta(hours=5)},
        )
        assert "sla_hours" in result[0]

    def test_missing_last_updated_treated_as_none(self):
        sla = FreshnessSLA("gold.test", 24.0, 26.0, 48.0)
        result = get_all_freshness(
            table_slas={"gold.test": sla},
            last_updated_map={},  # no last_updated for this table
        )
        assert len(result) == 1
        assert result[0]["status"] == FreshnessStatus.RED

    def test_empty_inputs_return_empty_list(self):
        result = get_all_freshness(table_slas={}, last_updated_map={})
        assert result == []

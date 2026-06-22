"""Energy-stat refinements: yesterday-so-far, month-end projection, 30-day
daily average, expanded base-load window, and the LTS annual override."""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from zoneinfo import ZoneInfo

import app.api.ha_proxy as hp
from app.services import ha_statistics


def _mk_points(reading_by_dt):
    """Build _parse_history-shaped points from {datetime: cumulative_kwh}."""
    return [{"time": dt.isoformat(), "value": v} for dt, v in reading_by_dt.items()]


def _boundaries(now):
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "today_start": today_start,
        "yesterday_start": today_start - timedelta(days=1),
        "seven_days_start": today_start - timedelta(days=7),
        "fourteen_days_start": today_start - timedelta(days=14),
        "thirty_days_start": today_start - timedelta(days=30),
        "month_start": today_start.replace(day=1),
    }


def test_yesterday_so_far_matches_elapsed_window():
    """yesterday_so_far covers yesterday only up to now's wall-clock time."""
    now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)  # noon today
    b = _boundaries(now)
    # Yesterday: +10 kWh by 11:00, +20 kWh by end of day. Today: +5 kWh so far.
    pts = _mk_points({
        b["yesterday_start"]: 100.0,
        b["yesterday_start"] + timedelta(hours=11): 110.0,   # before the noon cutoff
        b["yesterday_start"] + timedelta(hours=23, minutes=59): 120.0,
        now: 125.0,
    })
    stats = hp._compute_energy_stats(
        pts, b["today_start"], b["yesterday_start"], b["seven_days_start"],
        b["fourteen_days_start"], b["thirty_days_start"], b["month_start"], now,
    )
    assert stats["today"] == 5.0
    assert stats["yesterday"] == 20.0          # full yesterday
    assert stats["yesterday_so_far"] == 10.0   # yesterday up to noon


def test_month_end_estimate_extrapolates_to_full_month():
    """A steady daily pace projects to the calendar month's total."""
    now = datetime(2026, 6, 16, 0, 0, tzinfo=timezone.utc)  # 15 full days elapsed
    b = _boundaries(now)
    # 150 kWh over 15 days → 10 kWh/day → 300 kWh across June (30 days).
    pts = _mk_points({b["month_start"]: 1000.0, now: 1150.0})
    stats = hp._compute_energy_stats(
        pts, b["today_start"], b["yesterday_start"], b["seven_days_start"],
        b["fourteen_days_start"], b["thirty_days_start"], b["month_start"], now,
    )
    assert stats["this_month"] == 150.0
    assert stats["month_end_estimate"] == pytest.approx(300.0, abs=1.0)


def test_daily_avg_counts_only_days_with_data():
    """30-day average uses complete past days that have data; today excluded."""
    now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
    b = _boundaries(now)
    # Anchor at day -4 gives day -3 a baseline; days -3/-2/-1 each +5 kWh.
    # Today's partial day (+5) is excluded from the average.
    pts = _mk_points({
        b["today_start"] - timedelta(days=4): 0.0,
        b["today_start"] - timedelta(days=3): 5.0,
        b["today_start"] - timedelta(days=2): 10.0,
        b["today_start"] - timedelta(days=1): 15.0,
        b["today_start"]: 20.0,
        now: 25.0,
    })
    stats = hp._compute_energy_stats(
        pts, b["today_start"], b["yesterday_start"], b["seven_days_start"],
        b["fourteen_days_start"], b["thirty_days_start"], b["month_start"], now,
    )
    assert stats["daily_avg"] == 5.0
    assert stats["daily_avg_days"] == 3
    assert stats["annual_basis"] == "extrapolated"


def test_base_load_window_covers_two_to_four_local():
    """Base load averages readings in the local 02:00–04:00 window."""
    tz = ZoneInfo("Europe/Berlin")  # summer UTC+2
    points = [
        {"time": "2026-06-15T00:30:00+00:00", "value": 100.0},  # 02:30 local → in
        {"time": "2026-06-15T01:30:00+00:00", "value": 200.0},  # 03:30 local → in
        {"time": "2026-06-15T02:30:00+00:00", "value": 999.0},  # 04:30 local → out
        {"time": "2026-06-15T11:00:00+00:00", "value": -5000.0},  # daytime export
    ]
    stats = hp._compute_power_stats(points, tz)
    assert stats["base_load"] == 150.0  # mean(100, 200); export ignored, positive


@pytest.mark.asyncio
async def test_fetch_statistics_returns_none_without_token(monkeypatch):
    monkeypatch.setattr(ha_statistics, "SUPERVISOR_TOKEN", None)
    assert await ha_statistics.fetch_statistics("sensor.e", "2025-01-01T00:00:00+00:00") is None


@pytest.mark.asyncio
async def test_apply_longterm_stats_switches_to_lts_basis():
    """With ≥2 complete months, annual estimate becomes a rolling 12-mo average."""
    now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # 3 complete months at 300 kWh each + a partial current month.
    buckets = [
        {"start": "2026-03-01T00:00:00+00:00", "change": 300.0},
        {"start": "2026-04-01T00:00:00+00:00", "change": 300.0},
        {"start": "2026-05-01T00:00:00+00:00", "change": 300.0},
        {"start": "2026-06-01T00:00:00+00:00", "change": 150.0},  # current, partial
    ]
    energy_stats = {"annual_estimate": 1.0, "annual_basis": "extrapolated"}
    with patch.object(ha_statistics, "fetch_statistics", AsyncMock(return_value=buckets)):
        await hp._apply_longterm_stats(energy_stats, "sensor.e", today_start, now)
    assert energy_stats["annual_basis"] == "lts"
    assert energy_stats["annual_estimate"] == pytest.approx(3600.0, abs=1.0)  # 300*12


@pytest.mark.asyncio
async def test_apply_longterm_stats_keeps_extrapolation_on_failure():
    now = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    energy_stats = {"annual_estimate": 42.0, "annual_basis": "extrapolated"}
    with patch.object(ha_statistics, "fetch_statistics", AsyncMock(return_value=None)):
        await hp._apply_longterm_stats(energy_stats, "sensor.e", today_start, now)
    assert energy_stats["annual_estimate"] == 42.0
    assert energy_stats["annual_basis"] == "extrapolated"

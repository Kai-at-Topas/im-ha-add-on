"""Timezone handling for day/hour bucketing (Round 5).

Day boundaries, hourly buckets and the base-load window are computed in HA's
configured timezone rather than UTC so they match the user's wall clock.
"""
from datetime import timezone
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import app.api.ha_proxy as hp
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_tz_cache():
    """The resolved timezone is module-cached; reset around each test."""
    hp._ha_tz_cache = None
    yield
    hp._ha_tz_cache = None


@pytest.mark.asyncio
async def test_get_ha_tz_reads_config():
    with patch.object(hp.ha_client, "get_ha_config",
                      AsyncMock(return_value={"time_zone": "Europe/Berlin"})):
        tz = await hp._get_ha_tz()
    assert tz == ZoneInfo("Europe/Berlin")


@pytest.mark.asyncio
async def test_get_ha_tz_falls_back_to_utc():
    # No config (e.g. no token) → UTC
    with patch.object(hp.ha_client, "get_ha_config", AsyncMock(return_value=None)):
        assert await hp._get_ha_tz() == timezone.utc

    hp._ha_tz_cache = None
    # Bogus zone name → UTC
    with patch.object(hp.ha_client, "get_ha_config",
                      AsyncMock(return_value={"time_zone": "Mars/Phobos"})):
        assert await hp._get_ha_tz() == timezone.utc


@pytest.mark.asyncio
async def test_get_ha_tz_is_cached():
    mock = AsyncMock(return_value={"time_zone": "Europe/Berlin"})
    with patch.object(hp.ha_client, "get_ha_config", mock):
        await hp._get_ha_tz()
        await hp._get_ha_tz()
    mock.assert_awaited_once()


def test_time_endpoint_returns_ha_timezone():
    with patch.object(hp.ha_client, "get_ha_config",
                      AsyncMock(return_value={"time_zone": "Europe/Berlin"})):
        resp = client.get("/api/ha/time")
    assert resp.status_code == 200
    body = resp.json()
    assert body["time_zone"] == "Europe/Berlin"
    assert "utc_offset_minutes" in body and "now" in body


def test_time_endpoint_falls_back_to_utc():
    with patch.object(hp.ha_client, "get_ha_config", AsyncMock(return_value=None)):
        resp = client.get("/api/ha/time")
    assert resp.status_code == 200
    assert resp.json()["time_zone"] == "UTC"


def test_hourly_last_day_is_today():
    """Regression: /energy/hourly must include today as the last day (was
    off-by-one and ended at yesterday)."""
    from datetime import datetime, timezone, timedelta
    from types import SimpleNamespace

    now = datetime.now(timezone.utc)
    # Two readings today so there is real data in the final bucket-day.
    raw = [[
        {"entity_id": "sensor.e", "state": "100.0",
         "last_changed": (now - timedelta(hours=3)).isoformat(),
         "attributes": {"unit_of_measurement": "kWh"}},
        {"entity_id": "sensor.e", "state": "100.5",
         "last_changed": (now - timedelta(hours=1)).isoformat(),
         "attributes": {"unit_of_measurement": "kWh"}},
    ]]
    cfg = SimpleNamespace(energy_entity="sensor.e", power_entity=None)

    with patch.object(hp.ha_client, "get_ha_config", AsyncMock(return_value=None)), \
         patch.object(hp.config_manager, "read_config", return_value=cfg), \
         patch.object(hp.ha_client, "get_history", AsyncMock(return_value=raw)):
        resp = client.get("/api/ha/energy/hourly?days=7")

    body = resp.json()
    assert body["status"] == "ok"
    assert len(body["days"]) == 7
    assert body["days"][-1]["date"] == now.date().isoformat()  # today is last


def test_base_load_uses_local_night_window():
    tz = ZoneInfo("Europe/Berlin")  # summer: UTC+2
    # 00:30 UTC == 02:30 Berlin → inside the local 02:00–03:00 window
    points = [
        {"time": "2026-06-15T00:30:00+00:00", "value": 150.0},
        {"time": "2026-06-15T10:00:00+00:00", "value": 3000.0},
    ]
    assert hp._compute_power_stats(points, tz)["base_load"] == 150.0
    # Under UTC the same reading is at hour 0 → not in the window
    assert hp._compute_power_stats(points, timezone.utc)["base_load"] is None

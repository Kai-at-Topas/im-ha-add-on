import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config_manager import ConfigModel

client = TestClient(app)

# HA history responses are a list whose first element is the entity's series.
# With minimal_response, only the first sample carries full attributes.
POWER_HISTORY = [
    [
        {
            "entity_id": "sensor.power",
            "state": "100.0",
            "last_changed": "2026-06-05T10:00:00+00:00",
            "attributes": {"unit_of_measurement": "W"},
        },
        {"state": "150.0", "last_changed": "2026-06-05T10:05:00+00:00"},
        {"state": "unavailable", "last_changed": "2026-06-05T10:10:00+00:00"},
        {"state": "120.0", "last_changed": "2026-06-05T10:15:00+00:00"},
    ]
]


def _set_config(monkeypatch, power_entity=None, energy_entity=None):
    cfg = ConfigModel(power_entity=power_entity, energy_entity=energy_entity)
    monkeypatch.setattr("app.api.ha_proxy.config_manager.read_config", lambda: cfg)


def test_history_unconfigured(monkeypatch):
    """Null blocks when nothing is configured; HA is not queried."""
    _set_config(monkeypatch)
    mock = AsyncMock()
    with patch("app.api.ha_proxy.ha_client.get_history", mock):
        response = client.get("/api/ha/history")

    assert response.status_code == 200
    body = response.json()
    assert body["power"] is None
    assert body["energy"] is None
    mock.assert_not_called()


def test_history_parsed(monkeypatch):
    """A configured sensor yields normalized points; non-numeric samples are skipped."""
    _set_config(monkeypatch, power_entity="sensor.power")

    with patch("app.api.ha_proxy.ha_client.get_history", AsyncMock(return_value=POWER_HISTORY)):
        response = client.get("/api/ha/history?hours=24")

    assert response.status_code == 200
    power = response.json()["power"]
    assert power["entity_id"] == "sensor.power"
    assert power["unit"] == "W"
    assert [p["value"] for p in power["points"]] == [100.0, 150.0, 120.0]


def test_history_hours_clamped(monkeypatch):
    """The hours parameter is clamped to the allowed maximum."""
    _set_config(monkeypatch, power_entity="sensor.power")

    with patch("app.api.ha_proxy.ha_client.get_history", AsyncMock(return_value=POWER_HISTORY)):
        response = client.get("/api/ha/history?hours=100000")

    assert response.status_code == 200
    assert response.json()["hours"] == 168


def test_history_ha_unreachable(monkeypatch):
    """Null blocks when HA cannot be reached."""
    _set_config(monkeypatch, power_entity="sensor.power")

    with patch("app.api.ha_proxy.ha_client.get_history", AsyncMock(return_value=None)):
        response = client.get("/api/ha/history")

    assert response.status_code == 200
    assert response.json()["power"] is None

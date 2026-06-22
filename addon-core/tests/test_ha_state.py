import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config_manager import ConfigModel

client = TestClient(app)

WEATHER_STATE = {
    "entity_id": "weather.home",
    "state": "sunny",
    "attributes": {
        "temperature": 21.5,
        "temperature_unit": "°C",
        "humidity": 60,
        "wind_speed": 12,
        "wind_speed_unit": "km/h",
        "pressure": 1013,
    },
}

POWER_STATE = {
    "entity_id": "sensor.power",
    "state": "1234.0",
    "attributes": {
        "unit_of_measurement": "W",
        "device_class": "power",
    },
}

ENERGY_STATE = {
    "entity_id": "sensor.energy",
    "state": "4567.8",
    "attributes": {
        "unit_of_measurement": "kWh",
        "device_class": "energy",
    },
}


def _set_config(monkeypatch, weather_entity=None, power_entity=None, energy_entity=None):
    cfg = ConfigModel(
        weather_entity=weather_entity,
        power_entity=power_entity,
        energy_entity=energy_entity,
    )
    monkeypatch.setattr("app.api.ha_proxy.config_manager.read_config", lambda: cfg)


def test_state_unconfigured(monkeypatch):
    """Unset entities report status 'unconfigured'; HA is not queried."""
    _set_config(monkeypatch)
    mock_get_state = AsyncMock()
    with patch("app.api.ha_proxy.ha_client.get_state", mock_get_state):
        response = client.get("/api/ha/state")

    assert response.status_code == 200
    data = response.json()
    assert data["weather"] == {"status": "unconfigured"}
    assert data["power"] == {"status": "unconfigured"}
    assert data["energy"] == {"status": "unconfigured"}
    mock_get_state.assert_not_called()


def test_state_normalized(monkeypatch):
    """Configured, available entities are normalized with status 'ok'."""
    _set_config(monkeypatch, "weather.home", "sensor.power", "sensor.energy")

    async def fake_get_state(entity_id):
        return {
            "weather.home": WEATHER_STATE,
            "sensor.power": POWER_STATE,
            "sensor.energy": ENERGY_STATE,
        }[entity_id]

    with patch("app.api.ha_proxy.ha_client.get_state", side_effect=fake_get_state):
        response = client.get("/api/ha/state")

    assert response.status_code == 200
    data = response.json()
    assert data["weather"] == {
        "status": "ok",
        "entity_id": "weather.home",
        "condition": "sunny",
        "temperature": 21.5,
        "temperature_unit": "°C",
        "humidity": 60,
        "wind_speed": 12,
        "wind_speed_unit": "km/h",
        "pressure": 1013,
    }
    assert data["power"] == {
        "status": "ok",
        "entity_id": "sensor.power",
        "value": 1234.0,
        "unit": "W",
        "device_class": "power",
    }
    assert data["energy"]["status"] == "ok"
    assert data["energy"]["value"] == 4567.8


def test_state_unavailable_when_unreachable(monkeypatch):
    """Configured entities report 'unavailable' when HA cannot be reached."""
    _set_config(monkeypatch, "weather.home", "sensor.power", "sensor.energy")

    with patch("app.api.ha_proxy.ha_client.get_state", AsyncMock(return_value=None)):
        response = client.get("/api/ha/state")

    assert response.status_code == 200
    data = response.json()
    for block in (data["weather"], data["power"], data["energy"]):
        assert block["status"] == "unavailable"
    assert data["power"]["entity_id"] == "sensor.power"


def test_state_unavailable_when_state_unknown(monkeypatch):
    """A configured entity whose state is 'unavailable' reports 'unavailable'."""
    _set_config(monkeypatch, power_entity="sensor.power")
    bad_power = {
        "entity_id": "sensor.power",
        "state": "unavailable",
        "attributes": {"unit_of_measurement": "W", "device_class": "power"},
    }

    with patch("app.api.ha_proxy.ha_client.get_state", AsyncMock(return_value=bad_power)):
        response = client.get("/api/ha/state")

    assert response.status_code == 200
    assert response.json()["power"]["status"] == "unavailable"

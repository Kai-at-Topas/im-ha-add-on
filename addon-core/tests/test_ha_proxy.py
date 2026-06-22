import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

MOCK_STATES = [
    {
        "entity_id": "weather.home",
        "state": "sunny",
        "attributes": {"friendly_name": "Home", "temperature": 21.0},
        "last_changed": "2026-06-08T10:00:00Z",
    },
    {
        "entity_id": "weather.garden",
        "state": "cloudy",
        "attributes": {"friendly_name": "Garden"},  # no temperature → warn
        "last_changed": "2026-06-08T10:00:00Z",
    },
    {
        "entity_id": "sensor.electricity_consumption",
        "state": "4210.5",
        "attributes": {
            "device_class": "energy",
            "state_class": "total_increasing",
            "unit_of_measurement": "kWh",
            "friendly_name": "Grid Energy",
        },
        "last_changed": "2026-06-08T10:00:00Z",
    },
    {
        "entity_id": "sensor.total_power",
        "state": "1234.0",
        "attributes": {
            "device_class": "power",
            "state_class": "measurement",
            "unit_of_measurement": "W",
            "friendly_name": "Total Power",
        },
        "last_changed": "2026-06-08T10:00:00Z",
    },
    {"entity_id": "sensor.temperature", "state": "21.0", "attributes": {"device_class": "temperature"}, "last_changed": None},
    {"entity_id": "light.living_room", "state": "on", "attributes": {}, "last_changed": None},
]


def _mock_ha_client(states=MOCK_STATES):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = states

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(return_value=mock_resp)
    return mock_client


def test_entities_no_token(monkeypatch):
    """Returns empty lists when SUPERVISOR_TOKEN is not set."""
    monkeypatch.setattr("app.services.ha_client.SUPERVISOR_TOKEN", None)
    response = client.get("/api/ha/entities")
    assert response.status_code == 200
    assert response.json() == {"weather": [], "power": [], "energy": []}


def test_entities_filters_correctly(monkeypatch):
    """Weather, power and energy entities are returned as enriched objects.

    Checks: correct grouping, enriched fields present, validation assigned,
    ok-validated entries sorted before warn, and unrelated domains excluded.
    """
    monkeypatch.setattr("app.services.ha_client.SUPERVISOR_TOKEN", "test-token")

    with patch("app.services.ha_client.httpx2.AsyncClient", return_value=_mock_ha_client()):
        response = client.get("/api/ha/entities")

    assert response.status_code == 200
    data = response.json()

    # Correct grouping by entity_id
    weather_ids = [e["entity_id"] for e in data["weather"]]
    power_ids = [e["entity_id"] for e in data["power"]]
    energy_ids = [e["entity_id"] for e in data["energy"]]
    assert set(weather_ids) == {"weather.home", "weather.garden"}
    assert energy_ids == ["sensor.electricity_consumption"]
    assert power_ids == ["sensor.total_power"]

    # Unrelated entities excluded
    all_ids = weather_ids + power_ids + energy_ids
    assert "light.living_room" not in all_ids
    assert "sensor.temperature" not in all_ids

    # Enriched fields present
    power_entry = data["power"][0]
    assert power_entry["friendly_name"] == "Total Power"
    assert power_entry["value"] == 1234.0
    assert power_entry["unit"] == "W"
    assert power_entry["validation"]["status"] == "ok"

    energy_entry = data["energy"][0]
    assert energy_entry["value"] == 4210.5
    assert energy_entry["validation"]["status"] == "ok"

    # weather.home (has temperature) sorted before weather.garden (no temperature → warn)
    assert data["weather"][0]["entity_id"] == "weather.home"
    assert data["weather"][0]["validation"]["status"] == "ok"
    assert data["weather"][1]["validation"]["status"] == "warn"
    assert data["weather"][1]["validation"]["reason"] == "no_temperature"


def test_entities_ha_unreachable(monkeypatch):
    """Returns empty lists gracefully when HA cannot be reached."""
    monkeypatch.setattr("app.services.ha_client.SUPERVISOR_TOKEN", "test-token")

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

    with patch("app.services.ha_client.httpx2.AsyncClient", return_value=mock_client):
        response = client.get("/api/ha/entities")

    assert response.status_code == 200
    assert response.json() == {"weather": [], "power": [], "energy": []}

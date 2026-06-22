import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.core.config_manager import ConfigModel

client = TestClient(app)

SERVICE_RESPONSE = {
    "service_response": {
        "weather.home": {
            "forecast": [
                {
                    "datetime": "2026-06-06T12:00:00+00:00",
                    "condition": "sunny",
                    "temperature": 24,
                    "templow": 13,
                    "precipitation": 0,
                    "precipitation_probability": 5,
                },
                {
                    "datetime": "2026-06-07T12:00:00+00:00",
                    "condition": "rainy",
                    "temperature": 19,
                    "templow": 11,
                    "precipitation": 4.2,
                    "precipitation_probability": 80,
                },
            ]
        }
    }
}


def _set_config(monkeypatch, weather_entity=None):
    cfg = ConfigModel(weather_entity=weather_entity)
    monkeypatch.setattr("app.api.ha_proxy.config_manager.read_config", lambda: cfg)


def test_forecast_unconfigured(monkeypatch):
    _set_config(monkeypatch)
    mock = AsyncMock()
    with patch("app.api.ha_proxy.ha_client.get_forecast", mock):
        response = client.get("/api/ha/forecast")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "unconfigured"
    assert body["forecast"] == []
    mock.assert_not_called()


def test_forecast_parsed(monkeypatch):
    _set_config(monkeypatch, "weather.home")
    with patch("app.api.ha_proxy.ha_client.get_forecast", AsyncMock(return_value=SERVICE_RESPONSE)):
        response = client.get("/api/ha/forecast?type=daily")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["forecast"]) == 2
    assert body["forecast"][0]["condition"] == "sunny"
    assert body["forecast"][1]["temperature"] == 19
    assert body["forecast"][1]["precipitation_probability"] == 80


def test_forecast_unavailable(monkeypatch):
    _set_config(monkeypatch, "weather.home")
    with patch("app.api.ha_proxy.ha_client.get_forecast", AsyncMock(return_value=None)):
        response = client.get("/api/ha/forecast")

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"

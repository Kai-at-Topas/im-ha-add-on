import pytest
import os
import json
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.core.config_manager import ConfigManager


@pytest.fixture
def temp_config_file(tmp_path):
    config_file = tmp_path / "options.json"
    os.environ["CONFIG_PATH"] = str(config_file)
    from app import main
    mgr = ConfigManager(config_path=str(config_file))
    mgr.fallback_path = Path("/nonexistent/fallback.json")
    main.config_manager = mgr
    return config_file


@pytest.fixture
def client():
    return TestClient(app)


def test_get_config_defaults(client, temp_config_file):
    """Test that default configuration is returned when no file exists"""
    if temp_config_file.exists():
        temp_config_file.unlink()

    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["weather_entity"] is None
    assert data["energy_entity"] is None
    assert not data["mqtt_opt_in"]


def test_update_config_valid(client, temp_config_file):
    """Test updating configuration with valid data"""
    config_data = {
        "weather_entity": "weather.home",
        "energy_entity": "sensor.energy_usage",
        "mqtt_opt_in": True,
    }

    response = client.post("/api/config", json=config_data)
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    response = client.get("/api/config")
    assert response.json()["weather_entity"] == "weather.home"
    assert response.json()["energy_entity"] == "sensor.energy_usage"


def test_update_config_invalid_format(client, temp_config_file):
    """Test that invalid entity format throws validation error"""
    config_data = {
        "weather_entity": "invalid_entity",  # Missing dot
        "energy_entity": "sensor.energy.usage",  # Too many dots
        "mqtt_opt_in": True,
    }

    response = client.post("/api/config", json=config_data)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any("domain.name" in err["msg"] for err in errors)


def test_update_config_extra_fields(client, temp_config_file):
    """Test that extra fields are forbidden"""
    config_data = {
        "weather_entity": "weather.home",
        "extra_field": "not_allowed",
    }

    response = client.post("/api/config", json=config_data)
    assert response.status_code == 422


def test_config_corrupted_file(client, temp_config_file):
    """Test that corrupted JSON returns defaults"""
    temp_config_file.write_text("{ invalid json }")

    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert data["weather_entity"] is None  # Defaults


def test_accept_optin(client, temp_config_file):
    """Test the specialized opt-in endpoint"""
    temp_config_file.write_text(json.dumps({"mqtt_opt_in": False}))

    response = client.post("/api/config/optin")
    assert response.status_code == 200
    assert response.json()["mqtt_opt_in"]

    response = client.get("/api/config")
    assert response.json()["mqtt_opt_in"]


def test_update_config_partial(client, temp_config_file):
    """Test that partial updates merge with existing config"""
    initial_config = {
        "weather_entity": "weather.home",
        "energy_entity": "sensor.energy",
        "mqtt_opt_in": True,
    }
    temp_config_file.write_text(json.dumps(initial_config))

    update_data = {"weather_entity": "weather.new"}
    response = client.post("/api/config", json=update_data)
    assert response.status_code == 200

    response = client.get("/api/config")
    data = response.json()
    assert data["weather_entity"] == "weather.new"
    assert data["energy_entity"] == "sensor.energy"
    assert data["mqtt_opt_in"]


def test_mqtt_config_generator():
    """Test that generate_config_json5 fills all template placeholders."""
    from app.services.config_generator import generate_config_json5
    from app.core.config_manager import ConfigModel

    config = ConfigModel(
        power_entity="sensor.power",
        energy_entity="sensor.energy",
        mqtt_opt_in=True,
        mqtt_host="192.168.1.10",
        mqtt_port=1883,
        mqtt_user="user",
        mqtt_password="secret",
        mqtt_topic="home/energy",
    )
    output = generate_config_json5(config)

    assert "192.168.1.10" in output
    assert "1883" in output
    assert "user" in output
    assert "secret" in output
    assert "home/energy" in output
    assert "sensor.power" in output
    assert "sensor.energy" in output
    assert "{{" not in output

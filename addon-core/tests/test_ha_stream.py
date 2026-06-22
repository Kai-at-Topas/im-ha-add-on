import pytest
from unittest.mock import MagicMock, patch
from app.services.ha_stream import HAStreamService

@pytest.fixture
def stream_service():
    service = HAStreamService()
    service.last_energy_values = {}
    return service

@pytest.mark.asyncio
async def test_validation_invalid_states(stream_service, capsys):
    # Test unknown state
    await stream_service._handle_state_change(
        "sensor.test", {"state": "unknown"}, None, True
    )
    captured = capsys.readouterr()
    assert "[VALIDATION WARNING] Discarded invalid state: unknown" in captured.out

    # Test unavailable state
    await stream_service._handle_state_change(
        "sensor.test", {"state": "unavailable"}, None, True
    )
    captured = capsys.readouterr()
    assert "[VALIDATION WARNING] Discarded invalid state: unavailable" in captured.out

    # Test null state
    await stream_service._handle_state_change(
        "sensor.test", None, None, True
    )
    captured = capsys.readouterr()
    assert "[VALIDATION WARNING] Discarded invalid state: None" in captured.out

@pytest.mark.asyncio
async def test_energy_reset_validation(stream_service, capsys):
    entity = "sensor.energy_usage"
    
    energy_attrs = {"unit_of_measurement": "kWh", "device_class": "total_increasing"}

    # First valid reading
    await stream_service._handle_state_change(
        entity, {"state": "100.5", "attributes": energy_attrs}, None, True
    )
    assert stream_service.last_energy_values[entity] == 100.5

    # Second valid reading (increase)
    await stream_service._handle_state_change(
        entity, {"state": "105.2", "attributes": energy_attrs}, None, True
    )
    assert stream_service.last_energy_values[entity] == 105.2

    # Invalid reading (drop)
    await stream_service._handle_state_change(
        entity, {"state": "50.0", "attributes": energy_attrs}, None, True
    )
    captured = capsys.readouterr()
    assert "[VALIDATION WARNING] Discarded energy drop: 105.2 -> 50.0" in captured.out
    assert stream_service.last_energy_values[entity] == 105.2 # Should not update

@pytest.mark.asyncio
async def test_opt_in_reactive_lock(stream_service, capsys):
    # Test valid state but opt_in is False
    await stream_service._handle_state_change(
        "sensor.weather", {"state": "sunny"}, None, False
    )
    captured = capsys.readouterr()
    assert "Validated state change" not in captured.out

    # Test valid state but opt_in is True
    await stream_service._handle_state_change(
        "sensor.weather", {"state": "sunny", "attributes": {"unit_of_measurement": "°C"}}, None, True
    )
    captured = capsys.readouterr()
    assert "Validated state change -> Entity: sensor.weather | Value: sunny" in captured.out

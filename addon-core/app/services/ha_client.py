"""Home Assistant REST API client.

A thin async wrapper around HA's HTTP endpoints. Every function guards on
SUPERVISOR_TOKEN and returns None on failure so callers can degrade
gracefully without special-casing connection errors.

URL scheme:
    HA OS add-on:  HA_BASE_URL = http://supervisor/core  (Supervisor proxy)
    Standalone:    HA_BASE_URL = http://<host>:8123       (direct HA)
    Local dev:     HA_BASE_URL = http://localhost:8123
"""

import os
from typing import Any, Optional

import httpx2

HA_BASE_URL = os.getenv("HA_BASE_URL", "http://supervisor/core")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")

# Short timeout for single-entity lookups; longer for history which can
# return large payloads (up to a week of sensor readings).
REQUEST_TIMEOUT = 10.0
HISTORY_TIMEOUT = 20.0


def _headers() -> dict:
    return {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


async def get_states() -> Optional[list]:
    """Fetch all entity states from HA. Returns None if unavailable."""
    if not SUPERVISOR_TOKEN:
        print("[HA-CLIENT] SUPERVISOR_TOKEN not set — cannot fetch states.")
        return None

    try:
        async with httpx2.AsyncClient() as client:
            response = await client.get(
                f"{HA_BASE_URL}/api/states",
                headers=_headers(),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[HA-CLIENT] Failed to fetch states from HA: {e}")
        return None


async def get_state(entity_id: str) -> Optional[dict[str, Any]]:
    """Fetch a single entity's state from HA. Returns None if unavailable."""
    if not SUPERVISOR_TOKEN:
        print("[HA-CLIENT] SUPERVISOR_TOKEN not set — cannot fetch state.")
        return None

    try:
        async with httpx2.AsyncClient() as client:
            response = await client.get(
                f"{HA_BASE_URL}/api/states/{entity_id}",
                headers=_headers(),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[HA-CLIENT] Failed to fetch state for {entity_id}: {e}")
        return None


async def get_history(
    entity_id: str, start_iso: str, end_iso: Optional[str] = None
) -> Optional[list]:
    """Fetch an entity's state history from HA's History API.

    Returns the raw HA response (a list whose first element is the list
    of historical states for the entity), or None if unavailable.

    significant_changes_only keeps the payload small for fast-updating
    sensors (e.g. power) that would otherwise return tens of thousands
    of points over a day.
    """
    if not SUPERVISOR_TOKEN:
        print("[HA-CLIENT] SUPERVISOR_TOKEN not set — cannot fetch history.")
        return None

    params = {
        "filter_entity_id": entity_id,
        "minimal_response": "true",
        "significant_changes_only": "true",
    }
    if end_iso:
        params["end_time"] = end_iso

    try:
        async with httpx2.AsyncClient() as client:
            response = await client.get(
                f"{HA_BASE_URL}/api/history/period/{start_iso}",
                headers=_headers(),
                params=params,
                timeout=HISTORY_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(
            f"[HA-CLIENT] Failed to fetch history for {entity_id}: {e}"
        )
        return None


async def get_ha_config() -> Optional[dict]:
    """Fetch HA's global config (latitude, longitude, timezone, etc.)."""
    if not SUPERVISOR_TOKEN:
        print(
            "[HA-CLIENT] SUPERVISOR_TOKEN not set "
            "— cannot fetch HA config."
        )
        return None

    try:
        async with httpx2.AsyncClient() as client:
            response = await client.get(
                f"{HA_BASE_URL}/api/config",
                headers=_headers(),
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[HA-CLIENT] Failed to fetch HA config: {e}")
        return None


async def post_state(
    entity_id: str, state: str, attributes: Optional[dict] = None
) -> bool:
    """Create or update an entity state in HA via the REST states API.

    Returns True on success (HTTP 200 or 201), False on any failure.
    Creates the entity if it does not exist yet — useful for synthetic
    sensors like sensor.im_grid_usage that this add-on manages.
    """
    if not SUPERVISOR_TOKEN:
        return False

    body = {"state": state, "attributes": attributes or {}}
    try:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{HA_BASE_URL}/api/states/{entity_id}",
                headers=_headers(),
                json=body,
                timeout=REQUEST_TIMEOUT,
            )
            return response.status_code in (200, 201)
    except Exception as e:
        print(f"[HA-CLIENT] Failed to post state for {entity_id}: {e}")
        return False


async def delete_state(entity_id: str) -> bool:
    """Delete an ephemeral entity from HA's state machine.

    Returns True on 200 or 404 (already gone), False on other errors.
    Used during factory reset to remove synthetic sensors.
    """
    if not SUPERVISOR_TOKEN:
        return False
    try:
        async with httpx2.AsyncClient() as client:
            response = await client.delete(
                f"{HA_BASE_URL}/api/states/{entity_id}",
                headers=_headers(),
                timeout=REQUEST_TIMEOUT,
            )
            return response.status_code in (200, 404)
    except Exception as e:
        print(f"[HA-CLIENT] Failed to delete state {entity_id}: {e}")
        return False


async def get_forecast(
    entity_id: str, forecast_type: str = "daily"
) -> Optional[dict]:
    """Fetch a weather forecast via the weather.get_forecasts service.

    Modern HA exposes forecasts through a service call with response data
    rather than entity attributes. Returns the raw service response, or
    None if unavailable.
    """
    if not SUPERVISOR_TOKEN:
        print(
            "[HA-CLIENT] SUPERVISOR_TOKEN not set — cannot fetch forecast."
        )
        return None

    try:
        async with httpx2.AsyncClient() as client:
            response = await client.post(
                f"{HA_BASE_URL}/api/services/weather/get_forecasts",
                headers=_headers(),
                params={"return_response": "true"},
                json={"entity_id": entity_id, "type": forecast_type},
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(
            f"[HA-CLIENT] Failed to fetch forecast for {entity_id}: {e}"
        )
        return None

"""Home Assistant WebSocket stream service.

Maintains a persistent WebSocket connection to HA and listens for
state_changed events. Runs as a background asyncio task started during
FastAPI's lifespan startup so it shares the event loop with the ASGI
server and doesn't block API requests.

Event handling:
    Only events for the currently configured weather and energy entities
    are processed. When the user has opted in, validated state changes
    are logged (future: written to InfluxDB). When opted out, all events
    are silently discarded.

Validation:
    - Null / unavailable states are discarded.
    - Energy sensors with state_class=total_increasing are checked for
      backward jumps (meter reset or bad reading) and discarded if found.

Reconnection:
    On any WebSocket error the loop sleeps 10 s and retries indefinitely
    without blocking the API server or requiring a restart.
"""

import asyncio
import json
import os
from typing import Dict, Optional

import websockets

from ..core.config_manager import config_manager


class HAStreamService:
    """Background WebSocket listener for HA state_changed events."""

    def __init__(self):
        self.url = os.getenv(
            "HA_WS_URL", "ws://supervisor/core/websocket"
        )
        self.token = os.getenv("SUPERVISOR_TOKEN")
        # Tracks the last seen value for total_increasing energy sensors
        # so backward jumps (meter resets / bad readings) can be caught.
        self.last_energy_values: Dict[str, float] = {}
        self._running = False

    async def start(self):
        """Spawn the background listen loop as an asyncio task."""
        if not self.token:
            print(
                "[HA-STREAM] [ERROR] SUPERVISOR_TOKEN not found. "
                "Stream service disabled."
            )
            return

        self._running = True
        asyncio.create_task(self._listen_loop())

    async def stop(self):
        """Signal the listen loop to exit on the next iteration."""
        self._running = False

    async def _listen_loop(self):
        """Outer reconnect loop — wraps each WebSocket session."""
        print(
            "[HA-STREAM] Connecting to HA WebSocket "
            f"at {self.url}..."
        )

        while self._running:
            try:
                async with websockets.connect(self.url) as ws:
                    if await self._authenticate(ws):
                        await self._subscribe(ws)
                        await self._process_messages(ws)
            except Exception as e:
                if self._running:
                    print(
                        f"[HA-STREAM] [CONNECTION ERROR] {e}. "
                        "Retrying in 10s..."
                    )
                    await asyncio.sleep(10)

    async def _authenticate(self, ws) -> bool:
        """Run the HA auth handshake (auth_required -> auth_ok)."""
        auth_req = json.loads(await ws.recv())
        if auth_req.get("type") != "auth_required":
            return False

        await ws.send(json.dumps({
            "type": "auth",
            "access_token": self.token,
        }))

        auth_res = json.loads(await ws.recv())
        if auth_res.get("type") == "auth_ok":
            print("[HA-STREAM] Authenticated successfully.")
            return True

        print(
            f"[HA-STREAM] [AUTH ERROR] {auth_res.get('message')}"
        )
        return False

    async def _subscribe(self, ws):
        """Subscribe to all state_changed events."""
        await ws.send(json.dumps({
            "id": 1,
            "type": "subscribe_events",
            "event_type": "state_changed",
        }))
        print("[HA-STREAM] Subscribed to state_changed events.")

    async def _process_messages(self, ws):
        """Dispatch messages to the handler for tracked entities."""
        async for message in ws:
            if not self._running:
                break

            data = json.loads(message)
            event = data.get("event", {})
            if (
                data.get("type") != "event"
                or event.get("event_type") != "state_changed"
            ):
                continue

            event_data = event["data"]
            entity_id = event_data["entity_id"]

            current_config = config_manager.read_config()
            monitored = [
                current_config.weather_entity,
                current_config.energy_entity,
            ]

            if entity_id in monitored:
                await self._handle_state_change(
                    entity_id,
                    event_data.get("new_state"),
                    event_data.get("old_state"),
                    current_config.mqtt_opt_in,
                )

    async def _handle_state_change(
        self,
        entity_id: str,
        new_state: Optional[Dict],
        old_state: Optional[Dict],
        opt_in: bool,
    ):
        """Validate a state change and log it when opted in."""
        if not opt_in:
            return

        if not new_state or new_state.get("state") in (
            "unknown", "unavailable", None
        ):
            bad = new_state.get("state") if new_state else "None"
            print(
                "[HA-STREAM] [VALIDATION WARNING] Discarded "
                f"invalid state: {bad} for {entity_id}"
            )
            return

        state_value = new_state["state"]
        attributes = new_state.get("attributes", {})
        unit = attributes.get("unit_of_measurement", "")

        try:
            numeric_value: Optional[float] = float(state_value)
        except ValueError:
            # Non-numeric states (e.g. weather condition strings) are ok.
            numeric_value = None

        # Detect meter resets / bad readings for total_increasing sensors.
        if (
            attributes.get("device_class") == "total_increasing"
            and numeric_value is not None
        ):
            last_val = self.last_energy_values.get(entity_id)
            if last_val is not None and numeric_value < last_val:
                print(
                    "[HA-STREAM] [VALIDATION WARNING] Discarded "
                    f"energy drop: {last_val} -> {numeric_value} "
                    f"for {entity_id}"
                )
                return
            self.last_energy_values[entity_id] = numeric_value

        print(
            "[HA-STREAM] Validated state change -> "
            f"Entity: {entity_id} | Value: {state_value} "
            f"| Unit: {unit}"
        )


ha_stream_service = HAStreamService()

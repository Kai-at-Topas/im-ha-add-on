"""Home Assistant Long-Term Statistics (LTS) client.

LTS data (long-retention hourly/daily/monthly aggregates) is only exposed over
the WebSocket API via `recorder/statistics_during_period` — there is no REST
equivalent — so this lives separately from the REST `ha_client`. The auth
handshake mirrors `ha_stream._authenticate` (auth_required → auth → auth_ok).

Every call is fully guarded: any failure (missing token, unreachable HA,
recorder unsupported, malformed response) returns None so callers can fall back
to REST-derived estimates without crashing.
"""

import asyncio
import json
import os
from typing import Optional, Sequence

import websockets

WS_URL = os.getenv("HA_WS_URL", "ws://supervisor/core/websocket")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN")

# A single fetch should be quick; cap it so a slow/unresponsive recorder can't
# stall the /energy/stats endpoint.
CONNECT_TIMEOUT = 10.0


async def _authenticate(ws, token: str) -> bool:
    """Run the HA WebSocket auth handshake. Returns True on auth_ok."""
    auth_req = json.loads(await ws.recv())
    if auth_req.get("type") != "auth_required":
        return False

    await ws.send(json.dumps({"type": "auth", "access_token": token}))
    auth_res = json.loads(await ws.recv())
    if auth_res.get("type") == "auth_ok":
        return True

    print(f"[HA-STATS] [AUTH ERROR] {auth_res.get('message')}")
    return False


async def fetch_statistics(
    statistic_id: str,
    start_iso: str,
    end_iso: Optional[str] = None,
    period: str = "month",
    types: Sequence[str] = ("change",),
) -> Optional[list]:
    """Fetch LTS for one statistic via `recorder/statistics_during_period`.

    Returns the list of period buckets for `statistic_id` (each a dict with
    `start`, `end` and the requested `types`, e.g. `change`), or None on any
    failure so callers degrade gracefully.
    """
    if not SUPERVISOR_TOKEN:
        print("[HA-STATS] SUPERVISOR_TOKEN not set — cannot fetch statistics.")
        return None

    try:
        return await asyncio.wait_for(
            _fetch(statistic_id, start_iso, end_iso, period, types),
            timeout=CONNECT_TIMEOUT,
        )
    except Exception as e:  # noqa: BLE001 — intentional catch-all for graceful fallback
        print(f"[HA-STATS] Failed to fetch statistics for {statistic_id}: {e}")
        return None


async def _fetch(
    statistic_id: str,
    start_iso: str,
    end_iso: Optional[str],
    period: str,
    types: Sequence[str],
) -> Optional[list]:
    async with websockets.connect(WS_URL) as ws:
        if not await _authenticate(ws, SUPERVISOR_TOKEN):
            return None

        command = {
            "id": 1,
            "type": "recorder/statistics_during_period",
            "start_time": start_iso,
            "statistic_ids": [statistic_id],
            "period": period,
            "types": list(types),
        }
        if end_iso:
            command["end_time"] = end_iso

        await ws.send(json.dumps(command))

        # Skip any non-result frames until our command's response arrives.
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") != 1:
                continue
            if msg.get("type") != "result" or not msg.get("success"):
                print(f"[HA-STATS] Command failed: {msg.get('error')}")
                return None
            result = msg.get("result") or {}
            return result.get(statistic_id)

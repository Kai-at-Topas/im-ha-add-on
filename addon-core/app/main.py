"""HA Energy Dashboard — FastAPI application entry point.

Responsibilities:
- Registers the ha_proxy router (all /api/ha/* endpoints).
- Owns /api/config and /api/config/optin — config endpoints live here
  rather than in ha_proxy because they depend only on config_manager,
  not HA state.
- Starts the HA WebSocket stream service at startup via the lifespan
  context manager so it shares the event loop with the ASGI server.
- Mounts the compiled frontend (../static → frontend/dist) at / after
  all API routes so the SPA catches every unmatched path.

Boot order:
  uvicorn starts → lifespan enter → ha_stream_service.start() →
  routes available → yield → ha_stream_service.stop() on shutdown.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import ha_proxy
from app.core.config_manager import ConfigModel, config_manager
from app.services import ha_client, ha_statistics
from app.services.config_generator import write_config_json5
from app.services.energy_integrator import (
    HA_ENTITY_ID as _IM_ENTITY,
    HA_EXPORT_ENTITY_ID as _IM_EXPORT_ENTITY,
    energy_integrator as _integrator,
)
from app.services.ha_stream import ha_stream_service

# Keep in sync with addon-core/config.yaml
VERSION = "0.1.0"

INTEGRATION_INTERVAL = 60  # seconds between live integration ticks


def _mqtt_config_complete(cfg: ConfigModel) -> bool:
    """Return True when all MQTT fields are present and opt-in is active."""
    return bool(
        cfg.mqtt_opt_in
        and cfg.mqtt_host
        and cfg.mqtt_port
        and cfg.mqtt_user
        and cfg.mqtt_password
        and cfg.mqtt_topic
    )


def _maybe_write_mqtt_config(cfg: ConfigModel) -> None:
    """Write /config/config.json5 if MQTT is fully configured."""
    if _mqtt_config_complete(cfg):
        try:
            write_config_json5(cfg)
        except Exception as e:
            print(f"[CONFIG] Could not write MQTT config: {e}")


async def _backfill(power_entity: str) -> None:
    """Seed the integrator from historical data (LTS first, then REST).

    Uses up to 1 year of hourly LTS mean values if available; falls back
    to 30-day chunks of raw REST history. Skips silently on any failure
    so a missing history never blocks startup.
    """
    from datetime import timedelta

    one_year_ago = datetime.now(timezone.utc) - timedelta(days=365)
    start_iso = one_year_ago.isoformat()

    print(f"[IM] Starting backfill for {power_entity} from {start_iso[:10]}")

    # Try LTS hourly mean first (much less data than raw history)
    buckets = await ha_statistics.fetch_statistics(
        power_entity, start_iso, period="hour", types=("mean",)
    )
    if buckets:
        points = []
        for b in buckets:
            mean_w = b.get("mean")
            ts_str = b.get("start")
            if mean_w is None or ts_str is None:
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                points.append((float(mean_w), ts))
            except Exception:
                continue
        points.sort(key=lambda x: x[1])
        _integrator.backfill(points)
        _integrator.save()
        return

    # Fallback: REST history in 30-day chunks
    from datetime import timedelta as td

    points = []
    chunk_end = datetime.now(timezone.utc)
    chunk_start = chunk_end - td(days=30)
    for _ in range(12):  # up to 12 months
        raw = await ha_client.get_history(
            power_entity, chunk_start.isoformat(), chunk_end.isoformat()
        )
        if raw and raw[0]:
            for entry in raw[0]:
                state_str = entry.get("state", "")
                ts_str = (
                    entry.get("last_changed")
                    or entry.get("last_updated", "")
                )
                try:
                    power_w = float(state_str)
                    ts = datetime.fromisoformat(ts_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    points.append((power_w, ts))
                except Exception:
                    continue
        chunk_end = chunk_start
        chunk_start = chunk_end - td(days=30)
        if chunk_end <= one_year_ago:
            break

    points.sort(key=lambda x: x[1])
    _integrator.backfill(points)
    _integrator.save()


async def _integration_loop() -> None:
    """Background task: integrate live power readings every 60 seconds."""
    while True:
        await asyncio.sleep(INTEGRATION_INTERVAL)
        try:
            cfg = config_manager.read_config()
            if not cfg.power_entity:
                continue

            if _integrator.needs_reset(cfg.power_entity):
                _integrator.reset(cfg.power_entity)
                await _backfill(cfg.power_entity)

            state = await ha_client.get_state(cfg.power_entity)
            if state is None:
                continue

            raw = state.get("state", "")
            try:
                power_w = float(raw)
            except (ValueError, TypeError):
                continue

            _integrator.integrate(power_w, datetime.now(timezone.utc))
            _integrator.save()
            await _integrator.post_to_ha(ha_client)
        except Exception as e:
            print(f"[IM] Integration loop error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Seed power entity on startup and restore HA entity state
    cfg = config_manager.read_config()
    if cfg.power_entity:
        if _integrator.needs_reset(cfg.power_entity):
            _integrator.reset(cfg.power_entity)
            asyncio.create_task(_backfill(cfg.power_entity))
        else:
            # Re-create the HA entity after HA restart (it is ephemeral)
            await _integrator.post_to_ha(ha_client)

    await ha_stream_service.start()
    _loop_task = asyncio.create_task(_integration_loop())
    yield
    _loop_task.cancel()
    await ha_stream_service.stop()


app = FastAPI(title="HA Energy Dashboard API", lifespan=lifespan)

app.include_router(ha_proxy.router)


@app.get("/api/config")
async def get_config():
    """Return the current add-on configuration."""
    return config_manager.read_config()


@app.post("/api/config")
async def update_config(new_config: ConfigModel):
    """Merge new_config into the persisted configuration (partial update).

    Only fields present in the request body are overwritten; absent fields
    retain their current values. Logs a [SECURITY] event when
    mqtt_opt_in transitions from True to False (user revoked consent).
    After saving, generates /config/config.json5 if MQTT is fully configured.
    """
    current_config = config_manager.read_config()

    updated_data = current_config.model_dump()
    new_data = new_config.model_dump(exclude_unset=True)
    updated_data.update(new_data)

    merged_config = ConfigModel(**updated_data)

    if current_config.mqtt_opt_in and not merged_config.mqtt_opt_in:
        print(
            "[SECURITY] User revoked Terms of Service. "
            "External MQTT sync disabled."
        )

    config_manager.write_config(merged_config)
    _maybe_write_mqtt_config(merged_config)
    print(f"[CONFIG] Updated configuration: {new_data}")

    # If the power entity changed, reset the integrator and re-backfill
    if (
        "power_entity" in new_data
        and merged_config.power_entity
        and current_config.power_entity != merged_config.power_entity
    ):
        _integrator.reset(merged_config.power_entity)
        asyncio.create_task(_backfill(merged_config.power_entity))

    return {"status": "success"}


@app.post("/api/config/reset")
async def reset_config():
    """Reset configuration to factory defaults and clear integrator state."""
    config_manager.write_config(ConfigModel())
    _integrator.reset(None)
    _integrator.save()
    await ha_client.delete_state(_IM_ENTITY)
    await ha_client.delete_state(_IM_EXPORT_ENTITY)
    print("[CONFIG] Factory reset performed.")
    return {"status": "success"}


@app.post("/api/config/optin")
async def accept_optin():
    """Accept the Terms of Service and enable external MQTT streaming."""
    config = config_manager.read_config()
    config.mqtt_opt_in = True
    config_manager.write_config(config)
    print(
        "[SECURITY] User accepted Terms of Service. "
        "External MQTT sync authorized."
    )
    return {"status": "success", "mqtt_opt_in": True}


@app.get("/api/health")
async def health_check():
    """Liveness probe used by Docker health checks and the HA Supervisor."""
    return {"status": "healthy"}


@app.get("/api/version")
async def get_version():
    """Return the current add-on version. Mode is always 'standalone' until the
    add-on is published to the HA Add-on Store; at that point this endpoint can
    be extended to check the Supervisor API for update_available."""
    return {"current": VERSION, "mode": "standalone"}


# Static frontend mount — must come AFTER all API routes so the SPA
# catch-all does not swallow /api/* paths.
_static_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "static"
)
if os.path.exists(_static_dir):
    app.mount(
        "/", StaticFiles(directory=_static_dir, html=True), name="static"
    )

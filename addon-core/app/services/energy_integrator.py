"""Power-to-energy integrator for grid usage tracking.

Maintains a running integral of positive power readings (grid consumption)
and persists the result so it survives add-on restarts.  The integrated
value is also pushed to HA as a synthetic entity (sensor.im_grid_usage) so
it appears in the HA state machine and is recorded in HA's history.

Design decisions:
- Integration uses the trapezoidal rule between consecutive readings.
- Only integrates when power > 0 (grid consumption only; export is ignored).
- Skips integration when the gap between readings exceeds 30 minutes to
  avoid inflating the total during add-on downtime or HA restarts.
- Historical backfill is attempted on first run or after a power entity
  change, using LTS hourly statistics first (less data) then REST history.
- Entity state is re-posted to HA on every add-on startup so the synthetic
  entity is visible even after HA restarts (HA REST states are ephemeral).
"""

import json
import os
from datetime import datetime, timezone
from typing import Optional

MAX_GAP_SECONDS = 30 * 60  # 30 minutes — skip integration across larger gaps
HA_ENTITY_ID = "sensor.im_grid_usage_by_topas"
HA_EXPORT_ENTITY_ID = "sensor.im_grid_export_by_topas"


def _resolve_state_file() -> str:
    """Return a writable state file path, mirroring config_manager's fallback.
    """
    primary = os.getenv("IM_STATE_FILE", "/data/im_energy_state.json")
    parent = os.path.dirname(primary)
    if not parent or os.path.isdir(parent):
        return primary
    try:
        os.makedirs(parent, exist_ok=True)
        return primary
    except OSError:
        fallback = "./data/im_energy_state.json"
        try:
            os.makedirs(os.path.dirname(fallback), exist_ok=True)
        except OSError:
            pass
        print(f"[IM] /data not available, using fallback: {fallback}")
        return fallback


STATE_FILE = _resolve_state_file()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(iso: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


class EnergyIntegrator:
    """Stateful grid-usage integrator backed by a JSON persistence file."""

    def __init__(self) -> None:
        self.power_entity: Optional[str] = None
        self.grid_usage_kwh: float = 0.0
        self.grid_export_kwh: float = 0.0
        self.since_timestamp: str = _now_iso()
        self.last_reading_ts: Optional[str] = None
        self.last_power_w: float = 0.0
        self._dirty: bool = False

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load persisted state from disk.  Safe to call when file absent."""
        if not os.path.exists(STATE_FILE):
            return
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            self.power_entity = data.get("power_entity")
            self.grid_usage_kwh = float(data.get("grid_usage_kwh", 0.0))
            self.grid_export_kwh = float(data.get("grid_export_kwh", 0.0))
            self.since_timestamp = data.get("since_timestamp", _now_iso())
            self.last_reading_ts = data.get("last_reading_ts")
            self.last_power_w = float(data.get("last_power_w", 0.0))
            self._dirty = False
        except Exception as e:
            print(f"[IM] Could not load state from {STATE_FILE}: {e}")

    def save(self) -> None:
        """Write current state to disk."""
        try:
            data = {
                "power_entity": self.power_entity,
                "grid_usage_kwh": round(self.grid_usage_kwh, 6),
                "grid_export_kwh": round(self.grid_export_kwh, 6),
                "since_timestamp": self.since_timestamp,
                "last_reading_ts": self.last_reading_ts,
                "last_power_w": self.last_power_w,
            }
            with open(STATE_FILE, "w") as f:
                json.dump(data, f)
            self._dirty = False
        except Exception as e:
            print(f"[IM] Could not save state to {STATE_FILE}: {e}")

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def needs_reset(self, new_power_entity: str) -> bool:
        """True when the power entity has changed since last save."""
        return self.power_entity != new_power_entity

    def reset(self, power_entity: str) -> None:
        """Clear accumulated energy and start fresh for a new power entity."""
        self.power_entity = power_entity
        self.grid_usage_kwh = 0.0
        self.grid_export_kwh = 0.0
        self.since_timestamp = _now_iso()
        self.last_reading_ts = None
        self.last_power_w = 0.0
        self._dirty = True
        print(f"[IM] Reset integrator for entity {power_entity}")

    def get_state(self) -> dict:
        """Return a snapshot of the current integration state."""
        return {
            "power_entity": self.power_entity,
            "grid_usage_kwh": self.grid_usage_kwh,
            "grid_export_kwh": self.grid_export_kwh,
            "since_timestamp": self.since_timestamp,
        }

    # ------------------------------------------------------------------
    # Integration
    # ------------------------------------------------------------------

    def integrate(self, power_w: float, ts: datetime) -> None:
        """Apply a new power reading using the trapezoidal rule.

        Uses max(0, power_w) for consumption and max(0, -power_w) for export
        so both accumulators always update — even while exporting to the grid.
        Gaps larger than MAX_GAP_SECONDS are skipped to avoid inflating totals
        during add-on downtime or HA restarts.
        """
        ts_iso = ts.isoformat()

        if self.last_reading_ts is None:
            self.last_reading_ts = ts_iso
            self.last_power_w = power_w
            self._dirty = True
            return

        prev_dt = _parse_dt(self.last_reading_ts)
        if prev_dt is None:
            self.last_reading_ts = ts_iso
            self.last_power_w = power_w
            return

        gap_s = (ts - prev_dt).total_seconds()
        if gap_s <= 0:
            return  # out-of-order or duplicate reading

        if gap_s <= MAX_GAP_SECONDS:
            dt_h = gap_s / 3600.0
            # Trapezoidal rule, clamped per direction
            avg_usage = (max(0.0, self.last_power_w) + max(0.0, power_w)) / 2.0
            avg_export = (max(0.0, -self.last_power_w) + max(0.0, -power_w)) / 2.0
            self.grid_usage_kwh += avg_usage * dt_h / 1000.0
            self.grid_export_kwh += avg_export * dt_h / 1000.0

        self.last_reading_ts = ts_iso
        self.last_power_w = power_w
        self._dirty = True

    def backfill(self, points: list) -> None:
        """Batch-integrate a sorted list of (power_w, datetime) tuples.

        Used on first run or after a reset to seed the accumulated total
        from historical data before the add-on starts its live integration
        loop.  Respects the same gap and sign rules as integrate().
        """
        for power_w, ts in points:
            self.integrate(power_w, ts)
        print(
            f"[IM] Backfill complete: {len(points)} points, "
            f"{self.grid_usage_kwh:.3f} kWh so far"
        )

    # ------------------------------------------------------------------
    # HA entity publishing
    # ------------------------------------------------------------------

    async def post_to_ha(self, ha_client_module) -> None:
        """Push usage and export totals to HA as synthetic sensors."""
        src = self.power_entity or ""
        base_attrs = {
            "unit_of_measurement": "kWh",
            "device_class": "energy",
            "state_class": "total_increasing",
            "since": self.since_timestamp,
            "source_entity": src,
        }
        ok1 = await ha_client_module.post_state(
            HA_ENTITY_ID,
            str(round(self.grid_usage_kwh, 3)),
            {
                **base_attrs,
                "friendly_name": "IM Grid Usage by TOPAS",
                "icon": "mdi:transmission-tower-import",
            },
        )
        ok2 = await ha_client_module.post_state(
            HA_EXPORT_ENTITY_ID,
            str(round(self.grid_export_kwh, 3)),
            {
                **base_attrs,
                "friendly_name": "IM Grid Export by TOPAS",
                "icon": "mdi:transmission-tower-export",
            },
        )
        if not ok1:
            print("[IM] Could not post sensor.im_grid_usage_by_topas")
        if not ok2:
            print("[IM] Could not post sensor.im_grid_export_by_topas")


# Module-level singleton — loaded once on import so both main.py and
# ha_proxy.py can share the same live state without a circular import.
energy_integrator = EnergyIntegrator()
energy_integrator.load()

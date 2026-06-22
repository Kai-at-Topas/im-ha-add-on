import bisect
import calendar
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter

from ..core.config_manager import config_manager
from ..services import ha_client, ha_statistics
from ..services.energy_integrator import (
    HA_ENTITY_ID as _IM_ENTITY_ID,
    energy_integrator as _integrator,
)

router = APIRouter(prefix="/api/ha", tags=["Home Assistant Proxy"])

MAX_HISTORY_HOURS = 168  # one week

# Cached Home Assistant timezone. Day/hour boundaries are computed in this zone
# so the dashboard's "today", hourly buckets and "now" cutoff match the user's
# wall clock instead of UTC.
_ha_tz_cache = None


async def _get_ha_tz():
    """Return HA's configured timezone (cached), falling back to UTC.

    Reads `time_zone` from HA's /api/config. Falls back to UTC when the token
    is missing, the field is absent, or the zone can't be resolved.
    """
    global _ha_tz_cache
    if _ha_tz_cache is not None:
        return _ha_tz_cache

    tz = timezone.utc
    try:
        config = await ha_client.get_ha_config()
        name = config.get("time_zone") if config else None
        if name:
            tz = ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        print(f"[HA-CLIENT] Could not resolve HA timezone, using UTC: {exc}")

    _ha_tz_cache = tz
    return tz


def _validate_weather(attrs: dict) -> dict:
    if attrs.get("temperature") is None:
        return {"status": "warn", "reason": "no_temperature"}
    return {"status": "ok", "reason": None}


def _validate_power(attrs: dict) -> dict:
    if attrs.get("state_class") != "measurement":
        return {"status": "warn", "reason": "not_live"}
    return {"status": "ok", "reason": None}


def _validate_energy(attrs: dict) -> dict:
    if attrs.get("state_class") not in ("total", "total_increasing"):
        return {"status": "warn", "reason": "not_cumulative"}
    return {"status": "ok", "reason": None}


@router.get("/entities")
async def get_ha_entities():
    """Return selectable HA entities grouped by type, enriched with live state.

    Each entity entry includes friendly_name, current value, unit, and a
    validation block so the frontend can present a human-readable confirmation
    card instead of a raw entity-ID dropdown. Entries are sorted so validated
    (ok) candidates appear first — the frontend auto-selects the first one.
    """
    states = await ha_client.get_states()
    if states is None:
        return {"weather": [], "power": [], "energy": []}

    weather: list[dict] = []
    power: list[dict] = []
    energy: list[dict] = []

    for state in states:
        entity_id = state["entity_id"]
        domain = entity_id.split(".")[0]
        attrs = state.get("attributes", {})
        raw_value = state.get("state")
        last_updated = state.get("last_changed") or state.get("last_updated")
        friendly_name = attrs.get("friendly_name") or entity_id
        unit = attrs.get("unit_of_measurement")
        device_class = attrs.get("device_class", "")
        state_class = attrs.get("state_class", "")

        try:
            value: float | str | None = float(raw_value)
        except (TypeError, ValueError):
            value = raw_value if raw_value not in ("unavailable", "unknown") else None

        entry = {
            "entity_id": entity_id,
            "friendly_name": friendly_name,
            "unit": unit,
            "device_class": device_class,
            "state_class": state_class,
            "value": value,
            "last_updated": last_updated,
        }

        if domain == "weather":
            weather.append({**entry, "validation": _validate_weather(attrs)})
        elif domain == "sensor":
            if device_class == "power":
                power.append({**entry, "validation": _validate_power(attrs)})
            elif device_class == "energy":
                energy.append({**entry, "validation": _validate_energy(attrs)})

    def _ok_first(e: dict) -> int:
        return 0 if e["validation"]["status"] == "ok" else 1

    return {
        "weather": sorted(weather, key=_ok_first),
        "power": sorted(power, key=_ok_first),
        "energy": sorted(energy, key=_ok_first),
        "required": ["power"],
    }


def _normalize_weather(state: dict) -> dict:
    attrs = state.get("attributes", {})
    return {
        "entity_id": state["entity_id"],
        "condition": state.get("state"),
        "temperature": attrs.get("temperature"),
        "temperature_unit": attrs.get("temperature_unit"),
        "humidity": attrs.get("humidity"),
        "wind_speed": attrs.get("wind_speed"),
        "wind_speed_unit": attrs.get("wind_speed_unit"),
        "pressure": attrs.get("pressure"),
    }


def _normalize_sensor(state: dict) -> dict:
    attrs = state.get("attributes", {})
    raw_value = state.get("state")
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        value = None

    return {
        "entity_id": state["entity_id"],
        "value": value,
        "unit": attrs.get("unit_of_measurement"),
        "device_class": attrs.get("device_class"),
    }


# HA reports these as the entity's state when it has no usable value.
UNAVAILABLE_STATES = {"unavailable", "unknown", None}


async def _build_block(entity_id, normalize):
    """Return a status-tagged block for a configured entity.

    status is one of: 'unconfigured' (no entity set), 'unavailable'
    (configured but HA is unreachable or the entity has no usable state),
    or 'ok' (live data present).
    """
    if not entity_id:
        return {"status": "unconfigured"}

    state = await ha_client.get_state(entity_id)
    if state is None or state.get("state") in UNAVAILABLE_STATES:
        return {"status": "unavailable", "entity_id": entity_id}

    block = normalize(state)
    block["status"] = "ok"
    return block


@router.get("/state")
async def get_ha_state():
    """Return the current state of the configured entities.

    Each block carries a `status` so the UI can distinguish an unconfigured
    entity from a configured-but-unavailable one. The response is a
    dict-of-blocks so future blocks (e.g. forecast) can be added without
    breaking the frontend contract.
    """
    config = config_manager.read_config()

    # When no energy entity is configured but a power entity is set, fall back
    # to the integrated entity so the meter tile always shows a live kWh value.
    energy_id = config.energy_entity or (
        _IM_ENTITY_ID if config.power_entity else None
    )
    energy_block = await _build_block(energy_id, _normalize_sensor)
    if energy_id == _IM_ENTITY_ID and energy_block.get("status") == "ok":
        energy_block["source"] = "integrated"

    return {
        "weather": await _build_block(config.weather_entity, _normalize_weather),
        "power": await _build_block(config.power_entity, _normalize_sensor),
        "energy": energy_block,
    }


def _parse_history(raw) -> dict | None:
    """Normalize HA's history response into {entity_id, unit, points}."""
    if not raw or not raw[0]:
        return None

    series = raw[0]
    first = series[0]
    unit = first.get("attributes", {}).get("unit_of_measurement")

    # Normalize Wh → kWh so all downstream maths (period deltas, cost, hourly
    # matrix) operate in a single energy unit. We only expect Wh or kWh.
    wh_to_kwh = isinstance(unit, str) and unit.lower() == "wh"

    points = []
    for item in series:
        try:
            value = float(item.get("state"))
        except (TypeError, ValueError):
            continue  # skip 'unknown'/'unavailable'/non-numeric samples
        if wh_to_kwh:
            value /= 1000.0
        points.append(
            {"time": item.get("last_changed") or item.get("last_updated"), "value": value}
        )

    if wh_to_kwh:
        unit = "kWh"

    return {"entity_id": first.get("entity_id"), "unit": unit, "points": points}


async def _history_block(entity_id, start_iso, end_iso):
    if not entity_id:
        return None
    raw = await ha_client.get_history(entity_id, start_iso, end_iso)
    return _parse_history(raw) if raw is not None else None


@router.get("/history")
async def get_ha_history(hours: int = 24):
    """Return the recent history of the configured power and energy sensors.

    Blocks are null when the entity is unconfigured or unavailable. `hours`
    is clamped to a sane range.
    """
    hours = max(1, min(hours, MAX_HISTORY_HOURS))
    config = config_manager.read_config()

    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    start_iso = start.isoformat()
    end_iso = end.isoformat()

    return {
        "hours": hours,
        "power": await _history_block(config.power_entity, start_iso, end_iso),
        "energy": await _history_block(config.energy_entity, start_iso, end_iso),
    }


def _extract_forecast(raw, entity_id) -> list:
    """Pull the forecast list out of HA's get_forecasts service response.

    The response is shaped like {"service_response": {"<entity_id>":
    {"forecast": [...]}}}, but we navigate defensively across HA versions.
    """
    if not isinstance(raw, dict):
        return []

    container = raw.get("service_response", raw)
    entry = container.get(entity_id) if isinstance(container, dict) else None
    if isinstance(entry, dict) and isinstance(entry.get("forecast"), list):
        return entry["forecast"]

    # Fallback: first entity entry that carries a forecast list.
    if isinstance(container, dict):
        for value in container.values():
            if isinstance(value, dict) and isinstance(value.get("forecast"), list):
                return value["forecast"]
    return []


def _normalize_forecast(items: list) -> list:
    out = []
    for item in items:
        out.append(
            {
                "datetime": item.get("datetime"),
                "condition": item.get("condition"),
                "temperature": item.get("temperature"),
                "templow": item.get("templow"),
                "precipitation": item.get("precipitation"),
                "precipitation_probability": item.get(
                    "precipitation_probability"
                ),
                "wind_speed": item.get("wind_speed"),
            }
        )
    return out


WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _hourly_matrix(raw_points: list, start_day: datetime, days: int) -> list:
    """Build a list of day dicts, each with 24 hourly average-power values (W).

    Average power for an hour is derived from the cumulative energy meter:
    avg_W = (kWh consumed in the hour / hours elapsed) * 1000. raw_points is
    the output of _parse_history (already normalized to kWh). start_day must be
    midnight in the HA-configured timezone, so bucket index = local hour.
    Datetime comparisons are instant-based, so mixing the local-aware boundaries
    with the UTC-aware point timestamps is correct.

    A single sorted pass plus binary search keeps this O(n + buckets·log n)
    rather than re-scanning every point for each of the 24·days buckets.

    Future hours and hours with no baseline reading are returned as null; a
    flat meter (baseline exists, no change) yields 0.
    """
    if not raw_points:
        return []

    pts = []
    for p in raw_points:
        dt = _parse_ts(p["time"])
        if dt is not None:
            pts.append((dt, p["value"]))
    pts.sort(key=lambda x: x[0])

    if not pts:
        return []

    times = [dt for dt, _ in pts]
    values = [v for _, v in pts]
    first_time = times[0]

    def reading_at(boundary):
        # Cumulative value at `boundary` = last reading at-or-before it.
        # None when the boundary precedes the first reading (no baseline).
        if boundary < first_time:
            return None
        idx = bisect.bisect_right(times, boundary) - 1
        return values[idx] if idx >= 0 else None

    now = datetime.now(timezone.utc)
    result = []
    for day_offset in range(days):
        day_start = start_day + timedelta(days=day_offset)
        hours_list = []
        for hour in range(24):
            hour_start = day_start + timedelta(hours=hour)
            if hour_start >= now:
                hours_list.append(None)
                continue
            hour_end = min(hour_start + timedelta(hours=1), now)
            start_val = reading_at(hour_start)
            end_val = reading_at(hour_end)
            if start_val is None or end_val is None:
                hours_list.append(None)
                continue
            kwh = max(0.0, end_val - start_val)
            elapsed_h = (hour_end - hour_start).total_seconds() / 3600.0
            avg_w = (kwh * 1000.0 / elapsed_h) if elapsed_h > 0 else 0.0
            hours_list.append(round(avg_w, 1))
        result.append(
            {
                "date": day_start.date().isoformat(),
                "weekday": day_start.weekday(),
                "label": WEEKDAY_LABELS[day_start.weekday()],
                "hours": hours_list,
            }
        )
    return result


@router.get("/energy/hourly")
async def get_energy_hourly(days: int = 7):
    """Return hourly average power (W) for the past N days (max 30).

    Designed for heatmap and hourly-comparison chart visualisations. Values are
    average power per hour, derived from the cumulative energy meter. Each day
    entry contains 24 values (null for future hours or missing data).
    """
    days = max(1, min(days, 30))
    config = config_manager.read_config()

    if not config.energy_entity:
        return {"status": "unconfigured", "unit": None, "days": []}

    tz = await _get_ha_tz()
    now = datetime.now(tz)
    # Oldest day to display so the window is the last `days` days *including today*
    # (the matrix emits first_day … first_day+(days-1) == today).
    first_day = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    # Fetch one extra day earlier so the oldest day has a baseline reading for
    # the carry-forward delta of its first hour.
    history_start = first_day - timedelta(days=1)

    raw = await ha_client.get_history(
        config.energy_entity,
        history_start.isoformat(),
        now.isoformat(),
    )
    if raw is None:
        return {"status": "unavailable", "unit": None, "days": []}

    parsed = _parse_history(raw)
    if not parsed:
        return {"status": "unavailable", "unit": None, "days": []}

    return {
        "status": "ok",
        "unit": "W",
        "days": _hourly_matrix(parsed["points"], first_day, days),
    }


def _parse_ts(iso_str: str):
    """Return a timezone-aware datetime from an ISO string, or None."""
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _period_delta(pts: list, start_dt: datetime, end_dt: datetime):
    """Return energy delta for [start_dt, end_dt) from sorted (datetime, value) pairs.

    Uses the last reading before start_dt as baseline so consumption that began
    before the window is captured. Falls back to the first in-period reading
    when no prior reading exists.
    """
    before = [(dt, v) for dt, v in pts if dt < start_dt]
    in_period = [(dt, v) for dt, v in pts if start_dt <= dt < end_dt]

    if not in_period:
        # No readings inside the window. If a prior reading exists the meter
        # was simply flat → 0 consumption. Without any baseline it's unknown.
        return 0.0 if before else None
    if not before and len(in_period) < 2:
        return None

    baseline = before[-1][1] if before else in_period[0][1]
    delta = in_period[-1][1] - baseline
    return round(max(0.0, delta), 3)


def _compute_energy_stats(points, today_start, yesterday_start, seven_days_start, fourteen_days_start, thirty_days_start, month_start, now):
    if not points:
        return None

    pts = []
    for p in points:
        dt = _parse_ts(p["time"])
        if dt is not None:
            pts.append((dt, p["value"]))
    pts.sort(key=lambda x: x[0])

    if not pts:
        return None

    now_end = now + timedelta(seconds=1)

    today = _period_delta(pts, today_start, now_end)
    yesterday = _period_delta(pts, yesterday_start, today_start)
    # Yesterday up to the same wall-clock time as now — a fair "so far" comparison.
    elapsed_today = now - today_start
    yesterday_so_far = _period_delta(pts, yesterday_start, yesterday_start + elapsed_today)
    this_week = _period_delta(pts, seven_days_start, now_end)
    last_week = _period_delta(pts, fourteen_days_start, seven_days_start)
    this_month = _period_delta(pts, month_start, now_end)

    days_elapsed = max(1.0, (now - month_start).total_seconds() / 86400)
    annual_estimate = round((this_month / days_elapsed) * 365, 1) if this_month is not None else None

    # Projected month-end total: today's daily pace extended to every day of the
    # calendar month.
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    month_end_estimate = round((this_month / days_elapsed) * days_in_month, 1) if this_month is not None else None

    # Per-day totals for the last 7 calendar days (oldest → newest); the last
    # entry is today's partial total. Powers the consumption-card sparkline.
    daily = []
    for offset in range(6, -1, -1):
        day_start = today_start - timedelta(days=offset)
        day_end = min(day_start + timedelta(days=1), now_end)
        daily.append({
            "date": day_start.date().isoformat(),
            "label": WEEKDAY_LABELS[day_start.weekday()],
            "value": _period_delta(pts, day_start, day_end),
        })

    # 30-day daily average over *complete* past days (excludes today's partial
    # day). Only days with data count, so a short recorder window is reported
    # honestly via daily_avg_days.
    complete_day_totals = []
    for offset in range(30, 0, -1):
        day_start = today_start - timedelta(days=offset)
        if day_start < thirty_days_start:
            continue
        delta = _period_delta(pts, day_start, day_start + timedelta(days=1))
        if delta is not None:
            complete_day_totals.append(delta)
    daily_avg = round(sum(complete_day_totals) / len(complete_day_totals), 3) if complete_day_totals else None
    daily_avg_days = len(complete_day_totals)

    return {
        "today": today,
        "yesterday": yesterday,
        "yesterday_so_far": yesterday_so_far,
        "this_week": this_week,
        "last_week": last_week,
        "this_month": this_month,
        "month_end_estimate": month_end_estimate,
        "annual_estimate": annual_estimate,
        "annual_basis": "extrapolated",
        "daily_avg": daily_avg,
        "daily_avg_days": daily_avg_days,
        "daily": daily,
    }


async def _apply_longterm_stats(energy_stats: dict, statistic_id: str, today_start: datetime, now: datetime):
    """Refine the annual estimate from HA Long-Term Statistics (monthly change).

    Mutates `energy_stats` in place. On any failure (no LTS, recorder
    unsupported, too little history) the REST-derived extrapolation is kept and
    `annual_basis` stays "extrapolated". With ≥2 complete months we switch to a
    rolling 12-month average; with ≥13 months we also add a year-over-year
    comparison.
    """
    # Fetch ~14 months back so we have up to 13 complete months plus this one.
    lts_start = (today_start.replace(day=1) - timedelta(days=400)).isoformat()
    buckets = await ha_statistics.fetch_statistics(
        statistic_id, lts_start, now.isoformat(), period="month", types=("change",)
    )
    if not buckets:
        return

    # (month_start_dt, change) for every bucket that has a usable change value.
    months = []
    for b in buckets:
        change = b.get("change")
        start = _parse_ts(b.get("start"))
        if change is not None and start is not None:
            months.append((start, float(change)))
    months.sort(key=lambda x: x[0])
    if len(months) < 2:
        return

    # The last bucket is the current (incomplete) month — exclude from averages.
    complete = months[:-1]
    energy_stats["monthly"] = [{"month": s.date().isoformat(), "value": round(v, 3)} for s, v in months]

    recent = complete[-12:]
    avg_month = sum(v for _, v in recent) / len(recent)
    energy_stats["annual_estimate"] = round(avg_month * 12, 1)
    energy_stats["annual_basis"] = "lts"

    # Year-over-year: this calendar year so far vs the same span last year.
    vs_last_year_pct = None
    if len(months) >= 13:
        this_year = now.year
        ytd = sum(v for s, v in months if s.year == this_year and s.month <= now.month)
        prior = sum(v for s, v in months if s.year == this_year - 1 and s.month <= now.month)
        if prior > 0:
            vs_last_year_pct = round(((ytd - prior) / prior) * 100, 1)
    energy_stats["vs_last_year_pct"] = vs_last_year_pct


def _compute_power_stats(points, tz=timezone.utc):
    if not points:
        return None

    values = [p["value"] for p in points]
    if not values:
        return None

    # Base load: average of readings in the local 02:00–04:00 window — a
    # solar-free overnight window, so the average reflects always-on grid draw
    # and isn't dragged negative by daytime export.
    def _local_hour(p):
        dt = _parse_ts(p["time"])
        return dt.astimezone(tz).hour if dt else None

    night_vals = [max(0.0, p["value"]) for p in points if _local_hour(p) in (2, 3)]
    base_load = round(sum(night_vals) / len(night_vals), 1) if night_vals else None

    min_val = min(values)
    max_val = max(values)
    min_point = next(p for p in points if p["value"] == min_val)
    max_point = next(p for p in points if p["value"] == max_val)

    return {
        "base_load": base_load,
        "min_today": round(min_val, 1),
        "max_today": round(max_val, 1),
        "min_time": min_point["time"],
        "max_time": max_point["time"],
    }


def _compute_cost_stats(
    energy_stats, cost_per_kwh,
    annual_basic_price=None, month_start=None, now=None,
):
    no_cost = not cost_per_kwh or cost_per_kwh <= 0 or energy_stats is None
    if no_cost:
        return {
            "per_kwh": None, "today": None,
            "this_month": None, "annual_estimate": None,
            "today_grundpreis": None,
            "this_month_grundpreis": None,
            "annual_grundpreis": None,
        }

    def cost(val):
        if val is None:
            return None
        return round(val * cost_per_kwh, 2)

    daily_basic = round(annual_basic_price / 365, 2) if annual_basic_price else None
    if annual_basic_price and month_start and now:
        days_elapsed = max(1.0, (now - month_start).total_seconds() / 86400)
        monthly_basic = round(annual_basic_price * days_elapsed / 365, 2)
    else:
        monthly_basic = None

    return {
        "per_kwh": cost_per_kwh,
        "today": cost(energy_stats.get("today")),
        "this_month": cost(energy_stats.get("this_month")),
        "annual_estimate": cost(energy_stats.get("annual_estimate")),
        "today_grundpreis": daily_basic,
        "this_month_grundpreis": monthly_basic,
        "annual_grundpreis": round(annual_basic_price, 2) if annual_basic_price else None,
    }


@router.get("/location")
async def get_ha_location():
    """Return the home's latitude and longitude from HA's global config.

    Used by the rain radar map to centre on the user's home. Returns null
    fields when the supervisor token is absent or HA is unreachable.
    """
    raw = await ha_client.get_ha_config()
    if raw is None:
        return {"latitude": None, "longitude": None}
    return {
        "latitude": raw.get("latitude"),
        "longitude": raw.get("longitude"),
    }


@router.get("/time")
async def get_ha_time():
    """Return Home Assistant's timezone so the frontend can render time-of-day
    in HA's zone instead of the viewer's browser timezone.

    `time_zone` is the IANA name (e.g. "Europe/Berlin"), or "UTC" on fallback.
    `utc_offset_minutes` and `now` are provided for completeness.
    """
    tz = await _get_ha_tz()
    now = datetime.now(tz)
    offset = now.utcoffset()
    return {
        "time_zone": getattr(tz, "key", "UTC"),
        "utc_offset_minutes": int(offset.total_seconds() // 60) if offset else 0,
        "now": now.isoformat(),
    }


@router.get("/profile")
async def get_ha_profile():
    """Return the first HA person entity's friendly_name for the greeting.

    Falls back to null when no person entity exists or HA is unreachable.
    """
    states = await ha_client.get_states()
    if states:
        for s in states:
            if s.get("entity_id", "").startswith("person."):
                name = s.get("attributes", {}).get("friendly_name", "")
                if name:
                    return {"name": name}
    return {"name": None}


def _power_to_synth_energy(
    power_points: list, history_start: datetime, current_cumulative_kwh: float
) -> list:
    """Convert power history (W) to synthetic cumulative energy points (kWh).

    Accepts the same {"time": ..., "value": W} format produced by _parse_history.
    Returns a list in the same format with cumulative kWh values, scaled so the
    final point equals current_cumulative_kwh.  Returns an empty list when there
    are too few points or the integral is zero.
    """
    if len(power_points) < 2:
        return []

    # Parse timestamps and build running integral
    parsed = []
    for p in power_points:
        dt = _parse_ts(p["time"])
        if dt is not None:
            parsed.append((dt, float(p["value"])))
    parsed.sort(key=lambda x: x[0])

    if len(parsed) < 2:
        return []

    increments = []
    prev_ts, prev_w = parsed[0]
    total_delta = 0.0

    for ts, power_w in parsed[1:]:
        gap_s = (ts - prev_ts).total_seconds()
        if gap_s > 0:
            avg_w = (max(0.0, prev_w) + max(0.0, power_w)) / 2.0
            total_delta += avg_w * (gap_s / 3600.0) / 1000.0
        increments.append((ts.isoformat(), total_delta))
        prev_ts, prev_w = ts, power_w

    if not increments:
        return []

    if total_delta == 0.0:
        # Pure export period: return a flat line at the current cumulative so
        # period stats correctly show 0 consumption (not "unconfigured").
        return [
            {"time": increments[0][0], "value": current_cumulative_kwh},
            {"time": increments[-1][0], "value": current_cumulative_kwh},
        ]

    scale = current_cumulative_kwh / total_delta
    return [{"time": ts_iso, "value": v * scale} for ts_iso, v in increments]


@router.get("/energy/stats")
async def get_energy_stats():
    """Return pre-computed energy and power statistics for the configured entities.

    Derives period totals (today, yesterday, this/last week, this month) from
    cumulative energy sensor history and power analytics (peak, base load,
    min/max) from today's power history. Cost fields are null when cost_per_kwh
    is not configured or zero.
    """
    config = config_manager.read_config()

    if not config.energy_entity and not config.power_entity:
        return {"status": "unconfigured", "energy": None, "cost": None, "power": None}

    tz = await _get_ha_tz()
    now = datetime.now(tz)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    seven_days_start = today_start - timedelta(days=7)
    fourteen_days_start = today_start - timedelta(days=14)
    thirty_days_start = today_start - timedelta(days=30)
    month_start = today_start.replace(day=1)
    history_start = min(fourteen_days_start, thirty_days_start, month_start)

    energy_stats = None
    energy_unit = None
    energy_source = "entity"

    if config.energy_entity:
        raw = await ha_client.get_history(
            config.energy_entity,
            history_start.isoformat(),
            now.isoformat(),
        )
        parsed = _parse_history(raw) if raw else None
        if parsed:
            energy_unit = parsed["unit"]
            energy_stats = _compute_energy_stats(
                parsed["points"],
                today_start,
                yesterday_start,
                seven_days_start,
                fourteen_days_start,
                thirty_days_start,
                month_start,
                now,
            )
            await _apply_longterm_stats(energy_stats, config.energy_entity, today_start, now)

    # Fallback: derive energy stats from the power integrator when no energy
    # entity is configured or its history returned no usable data.
    if energy_stats is None and config.power_entity:
        # Always use the integrator when a power entity is configured —
        # even during export (grid_usage_kwh may be 0 early on).
        integrator_state = _integrator.get_state()
        energy_source = "integrated"
        energy_unit = "kWh"
        raw_power = await ha_client.get_history(
            config.power_entity,
            history_start.isoformat(),
            now.isoformat(),
        )
        parsed_power = _parse_history(raw_power) if raw_power else None
        if parsed_power:
            cumulative_kwh = integrator_state["grid_usage_kwh"]
            synth_points = _power_to_synth_energy(
                parsed_power["points"], history_start, cumulative_kwh
            )
            if synth_points:
                energy_stats = _compute_energy_stats(
                    synth_points,
                    today_start,
                    yesterday_start,
                    seven_days_start,
                    fourteen_days_start,
                    thirty_days_start,
                    month_start,
                    now,
                )
                if energy_stats:
                    energy_stats["since_timestamp"] = integrator_state.get(
                        "since_timestamp"
                    )
                    energy_stats["annual_basis"] = "integrated"

    power_stats = None
    power_unit = None
    if config.power_entity:
        raw = await ha_client.get_history(
            config.power_entity,
            today_start.isoformat(),
            now.isoformat(),
        )
        parsed = _parse_history(raw) if raw else None
        if parsed:
            power_unit = parsed["unit"]
            power_stats = _compute_power_stats(parsed["points"], tz)

    return {
        "status": "ok",
        "energy_source": energy_source,
        "energy": {**energy_stats, "unit": energy_unit} if energy_stats else None,
        "cost": _compute_cost_stats(
            energy_stats, config.cost_per_kwh,
            config.annual_basic_price, month_start, now,
        ),
        "power": {**power_stats, "unit": power_unit} if power_stats else None,
    }


@router.get("/forecast")
async def get_ha_forecast(type: str = "daily"):
    """Return the forecast for the configured weather entity.

    `status` mirrors /state: unconfigured | unavailable | ok.
    """
    config = config_manager.read_config()
    if not config.weather_entity:
        return {"status": "unconfigured", "type": type, "forecast": []}

    raw = await ha_client.get_forecast(config.weather_entity, type)
    if raw is None:
        return {"status": "unavailable", "type": type, "forecast": []}

    forecast = _normalize_forecast(_extract_forecast(raw, config.weather_entity))
    return {"status": "ok", "type": type, "forecast": forecast}

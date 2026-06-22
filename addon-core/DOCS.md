# IM Energy Dashboard — Documentation

## Overview

This add-on serves a Vue.js dashboard through Home Assistant Ingress,
backed by a FastAPI service. It reads weather and energy entities from
your Home Assistant instance via the Supervisor API and visualises them
across four rows:

- **Row 1** — Live power (signed: grid import / solar export), cumulative
  meter reading, and current weather conditions with a sparkline history
  for each.
- **Row 2** — Period energy summaries: today vs yesterday-at-this-time,
  this month with a month-end projection, and an annual estimate (rolling
  12-month average when Long-Term Statistics are available, otherwise an
  extrapolation from the current month's daily pace).
- **Row 3** — Daily consumption bars: today / yesterday / 30-day average,
  with percentage comparison badges.
- **Row 4** — Power analysis: base load (average overnight draw), and
  today's peak solar export and peak grid usage with timestamps.

## First steps

1. Start the add-on and open it from the sidebar.
2. Go to **Settings** inside the dashboard.
3. Pick your entities:
   - **Weather entity** — a `weather.*` entity.
   - **Power entity** — a sensor with device class `power` (e.g. watts).
     Negative values are interpreted as solar export.
   - **Energy entity** — a sensor with device class `energy` (e.g. kWh,
     cumulative meter).
4. Optionally set an **electricity price** (€/kWh) to enable cost tiles.
5. Save. The dashboard refreshes automatically on a short polling interval.

## Configuration options

| Option | Type | Notes |
|---|---|---|
| `weather_entity` | string | Format `domain.name`, e.g. `weather.home`. |
| `power_entity` | string | Instantaneous power sensor. Negative = solar export. |
| `energy_entity` | string | Cumulative energy sensor (kWh or Wh; Wh is auto-converted). |
| `cost_per_kwh` | float | Electricity price in €/kWh. Leave empty to hide cost tiles. |
| `annual_basic_price` | float | Optional fixed annual price component (€/year). |
| `mqtt_opt_in` | bool | Master switch for external data synchronisation. |
| `mqtt_host` | string | MQTT broker host. |
| `mqtt_port` | int | MQTT broker port (default 1883). |
| `mqtt_user` | string | MQTT username. |
| `mqtt_password` | string | MQTT password. |
| `mqtt_topic` | string | Target MQTT topic. |

> The external MQTT delivery backend is delivered in version 0.2.0; these
> fields configure it ahead of time.

These options can be edited from the add-on configuration tab or from the
dashboard's own Settings page. Changes take effect immediately without
restarting the add-on.

## Privacy & data synchronisation

The dashboard operates entirely on local Home Assistant data. **No data is
sent to any external server unless you explicitly opt in.**

- **Opt-in** enables forwarding of weather/energy metadata (entity IDs and
  state values) to an external MQTT broker for long-term analysis.
- You can **enable** it from the dashboard Settings page (or the standalone
  consent page at `/#/opt-in`) and **revoke** it there at any time.
- Revoking immediately stops all external streaming. The dashboard remains
  fully usable in either state.

## Troubleshooting

- **Empty entity lists / no live values:** the add-on needs Supervisor API
  access (`hassio_api: true`, granted automatically in HA OS). In a
  standalone container, provide `SUPERVISOR_TOKEN` and `HA_BASE_URL` (see
  the repository root `README.md`).
- **Forecast unavailable:** your weather integration must support the
  `weather.get_forecasts` service (standard since HA 2024.x).
- **Annual estimate shows "Based on previous months" instead of vs last
  year:** Long-Term Statistics need at least 13 months of data in the HA
  recorder. The estimate will still be accurate — it uses LTS monthly
  averages once 2+ complete months are available.
- **Base load shows "Calculated nightly":** no power readings were found
  between 02:00–04:00 local time today. This clears automatically once
  the overnight window passes.

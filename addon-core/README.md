# IM Energy Dashboard

A weather & energy dashboard for Home Assistant. Shows current weather
conditions and live power/energy readings from your own HA entities, with
signed grid export/import display, history sparklines, consumption bar
charts, power analysis (base load, min/max), and a weather forecast.
Light/dark mode and German/English language switch included.

The dashboard runs entirely on local Home Assistant data and sends nothing
externally by default. An optional **data synchronization (opt-in)** can
forward metadata to an external MQTT broker — this is off by default and the
dashboard is fully usable without it. The MQTT delivery backend is delivered
in version 0.1.1.

## Installation

1. In Home Assistant, go to **Settings → Add-ons** (labelled **"Apps"** in
   newer Home Assistant versions) **→ Add-on Store**.
2. Open the **⋮** menu (top right) → **Repositories**.
3. Add this repository URL:
   ```
   https://github.com/Kai-at-Topas/im-ha-add-on
   ```
4. Find **IM Energy Dashboard** in the store and click **Install**.
5. Start the add-on and open it from the sidebar (Ingress).

> Running Home Assistant in a container instead of HA OS? See the
> repository root `README.md` for a `docker-compose.yml` based setup.

## Configuration

Most settings are managed from the dashboard's own **Settings** page, but
they are also exposed as add-on options:

| Option | Description |
|---|---|
| `weather_entity` | A `weather.*` entity (current conditions, temperature, humidity, wind). |
| `power_entity` | A sensor with device class `power` (instantaneous consumption in W). |
| `energy_entity` | A sensor with device class `energy` (cumulative meter in kWh). |
| `cost_per_kwh` | Optional electricity price (€/kWh). Enables cost tiles on the dashboard. |
| `annual_basic_price` | Optional fixed annual price component (€/year). |
| `mqtt_opt_in` | Enables external data synchronization (off by default). |
| `mqtt_host` / `mqtt_port` / `mqtt_user` / `mqtt_password` / `mqtt_topic` | MQTT broker connection details (used only when opted in; full delivery backend arrives in 0.1.1). |

## Privacy

External data synchronization is **opt-in**. While disabled, no metadata
leaves your Home Assistant instance. You can enable or revoke it at any
time from the dashboard's Settings page. See `DOCS.md` for details.

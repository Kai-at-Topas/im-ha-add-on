# Changelog

## 0.1.1

- Fixed: declare `homeassistant_api` so the add-on can reach the Home Assistant
  Core API (entities, states, profile, history). Without it, entity and name
  lookups returned nothing.
- Dropped the 32-bit ARM (`armv7`) image; only `amd64` and `aarch64` are built.
- CI: bumped `actions/checkout` to v5 (Node 24 runtime).

## 0.1.0

Initial release.

- Weather & energy dashboard served through Home Assistant Ingress.
- Live current weather (condition, temperature, humidity, wind, pressure) and
  live power/energy readings, with history charts and a weather forecast.
- Light/dark mode and German/English language switches.
- Configurable entities and electricity price, editable from the dashboard or
  the add-on options.
- Dashboard usable without opt-in; optional external data synchronization
  (MQTT, opt-in) is off by default and can be enabled/revoked from Settings.
  The full MQTT delivery backend is delivered in version 0.2.0.
- Multi-arch images (amd64, aarch64) published to GHCR.

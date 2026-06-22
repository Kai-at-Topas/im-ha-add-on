# IM Energy Dashboard

A Home Assistant add-on providing a weather & energy dashboard. Runs entirely
on local Home Assistant data by default, with an optional, privacy-first opt-in
for external data synchronization.

## Project Vision
- **Ingress-Ready:** Seamlessly integrates into the Home Assistant sidebar.
- **Dual-Target Frontend:** Compiled for both a full-screen Ingress App and a Custom Lovelace Card.
- **Configurable:** Live entity selection populated directly from your Home Assistant instance.
- **Compliant:** Strict legal opt-in page before any external data synchronization.
- **Streaming:** Normalizes and streams data to an external MQTT broker (opt-in; the full MQTT delivery backend is delivered in version 0.1.1).

## Architecture
- **Backend:** FastAPI (Python 3.12) - Handles configuration management, HA entity proxying, and background WebSocket streaming.
- **Frontend:** Vue.js 3 + Vite + TailwindCSS - Optimized for HA Ingress using relative paths and hash history.

## Installation

> Multi-arch images (`amd64`, `aarch64`, `armv7`) are published to GHCR by
> `.github/workflows/build.yml` when a `v*` tag is pushed.

### Home Assistant OS (Add-on Store)
1. **Settings → Add-ons** (labelled **"Apps"** in newer Home Assistant versions) **→ Add-on Store**.
2. **⋮** menu → **Repositories** → add `https://github.com/Kai-at-Topas/im-ha-add-on`.
3. Install **IM Energy Dashboard**, start it, and open it from the sidebar.

The Supervisor pulls the prebuilt image (`ghcr.io/kai-at-topas/{arch}-ha-energy-dashboard`)
— no local build required. See [`addon-core/README.md`](addon-core/README.md) and
[`addon-core/DOCS.md`](addon-core/DOCS.md) for configuration details.

### Home Assistant in a container (standalone Docker)
Use the provided [`docker-compose.yml`](docker-compose.yml). Fill in the environment
variables (token + HA URLs, documented below) and run:

```bash
docker compose up -d
```

The dashboard is then available at `http://<host>:9150`.

## Getting Started

### Prerequisites
- Node.js 20+
- Python 3.12+
- Docker (optional, for full build)

### Environment Variables

| Variable | Default (production) | Description |
|---|---|---|
| `SUPERVISOR_TOKEN` | — | HA Supervisor token (auto-injected in add-on) |
| `HA_BASE_URL` | `http://supervisor/core` | Base URL for the HA REST API |
| `HA_WS_URL` | `ws://supervisor/core/websocket` | WebSocket URL for HA state events |
| `CONFIG_PATH` | `/data/options.json` | Config file location |

> **Note:** The REST and WebSocket paths differ between the Supervisor proxy and a direct HA instance:
> - Supervisor: `http://supervisor/core/api/...` and `ws://supervisor/core/websocket`
> - Direct (local dev): `http://localhost:8123/api/...` and `ws://localhost:8123/api/websocket`

### Local Development

#### 1. Backend Setup
```bash
cd addon-core
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

HA_BASE_URL=http://localhost:8123 \
HA_WS_URL=ws://localhost:8123/api/websocket \
SUPERVISOR_TOKEN=<your-long-lived-token> \
CONFIG_PATH=data/options.json \
python -m uvicorn app.main:app --host 0.0.0.0 --port 9150 --reload
```

Without `SUPERVISOR_TOKEN` the entity list returns empty and the stream is disabled — the UI still works for testing config and routing.

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev  # Vite dev server at http://localhost:5173, proxies /api to port 9150
```

#### 3. Integrated Local Build
To test the production build locally without Docker:
```bash
cd frontend && npm run build
cd ../addon-core
ln -s ../frontend/dist static
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9150
```

### Running Tests
```bash
cd addon-core
pytest          # all tests
pytest -v       # verbose
```

### Building the Add-on (Docker)
The `Dockerfile` at the repository root uses a multi-stage build to compile the frontend and backend together. Run from the **project root**:

```bash
docker build -t im-ha .
```

> Publishing this add-on to GitHub + GHCR so Home Assistant can install it?
> See [`PUBLISHING.md`](PUBLISHING.md) for the full release runbook.

## Configuration
The add-on manages its state in `/data/options.json` (as per HA standards). Locally, it defaults to `addon-core/data/options.json`.

## License
Licensed under the [Apache License 2.0](LICENSE).

# Meshviewer

Vue 3 Single Page App served by Nginx with a Django REST API (DRF) backend. The stack is designed as a headless/decoupled SPA with JSON over REST and an optional Meshcore CLI integration for device connectivity over Wi‑Fi.

- Vue 3 + Vite + Tailwind SPA (static build served by Nginx)
- Django + DRF backend with JWT auth and CORS
- Nginx reverse proxy for the API (`/api/v1/...`)
- Optional Meshcore CLI usage to talk to your device over Wi‑Fi
- PostgreSQL database, Docker-based dev/prod setup

Tip: This README is intentionally comprehensive to help you run, develop, and deploy the project end‑to‑end. If you only need the short path, jump to Quickstart.


## Screenshots

https://ibb.co/35xs63Gh

https://ibb.co/s9hS696H



## Quickstart

1) Copy the environment template and adjust values:

```
cp .env.example .env
```

Key variables you must set immediately:
- `DJANGO_SECRET_KEY` — any non-empty value for local dev
- `HTTP_PORT` — default 80; change if occupied
- `POSTGRES_*` — defaults work with the bundled `db` service
- `MESHCORE_TARGET` — IP or host:port of your device Wi‑Fi companion (see Wi‑Fi Companion Firmware below)

2) Build and start the stack:

```
docker compose build
docker compose up -d
```

3) Open the app:
- Frontend: `http://localhost:${HTTP_PORT}`
- API health: `http://localhost:${HTTP_PORT}/api/v1/health/`

To stop: `docker compose down` (add `-v` to remove volumes/data).

## Architecture

- Frontend: Vue 3 + Vite + Tailwind. Built into static files and served by Nginx. Router-based SPA with dark mode and responsive UI.
- Backend: Django + DRF. REST endpoints under `/api/v1/...`, JWT auth, CORS for local dev, PostgreSQL storage.
- Reverse proxy: Nginx serves the SPA and proxies API calls to the Django service. Requests to `/api/...` are forwarded to the backend, which exposes `/v1/...` internally.
- Optional device connectivity: Meshcore CLI is used by the backend and collectors to query device info (via `MESHCORE_TARGET`).

## Features

- Dashboard: Aggregated kpis, node info, quick links to Messages and Map
- Contacts: Latest contacts with telemetry (RSSI/SNR/battery/location when available)
- Messages: View and send chat messages to nodes; basic delivery status
- Automations: Simple rules engine (autoresponse and MQTT actions)
- Settings: Collector interval and options, MQTT broker settings with live connection test

## Wi‑Fi Companion Firmware (Required)

To connect over Wi‑Fi, you need a small “Wi‑Fi companion” firmware running on a microcontroller (commonly ESP32/ESP8266). This firmware bridges your mesh device to TCP/IP so `meshcore-cli` (and this backend) can talk to it via `-t <ip[:port]>`.

Important:
- You currently need to build the companion firmware yourself.
- Provide your Wi‑Fi credentials at compile time. The companion has no UI to configure them later.

Typical build approaches
- PlatformIO (recommended)
  - Add compile-time defines in `platformio.ini`:
    
    ```ini
    [env:esp32dev]
    platform = espressif32
    board = esp32dev
    framework = arduino
    build_flags =
      -D WIFI_SSID="YourSSID"
      -D WIFI_PASS="YourPassword"
    ```
  - Then build and upload: `pio run -t upload`

- Arduino IDE / Arduino CLI
  - Define credentials in a header file (do not commit secrets):
    
    ```c
    // secrets.h
    #pragma once
    #define WIFI_SSID "YourSSID"
    #define WIFI_PASS "YourPassword"
    ```
    
    And include it from your main sketch.
  - Alternatively pass defines at compile time with Arduino CLI:
    
    ```bash
    arduino-cli compile \
      --fqbn esp32:esp32:esp32 \
      --build-property "compiler.c.extra_flags=-D WIFI_SSID=\"YourSSID\" -D WIFI_PASS=\"YourPassword\"" \
      --build-property "compiler.cpp.extra_flags=-D WIFI_SSID=\"YourSSID\" -D WIFI_PASS=\"YourPassword\"" \
      .
    arduino-cli upload --port /dev/ttyUSB0 --fqbn esp32:esp32:esp32 .
    ```

After flashing
- The device joins your Wi‑Fi using the credentials you compiled in.
- Find its IP (check your router/DHCP, serial logs, or mDNS if available).
- Set `MESHCORE_TARGET=<ip>` (or `<ip:port>` if your firmware uses a custom port) in `.env` so the backend and collectors can reach it.

Security note: Do not hard-code production credentials in versioned files. Use local-only `secrets.h` or CI/CD secrets for production builds.

## Meshcore CLI Integration

The backend uses `meshcore-cli` for one-shot JSON calls (e.g., `infos`, `self_telemetry`, `contacts`) and for interactive sessions when needed. You can customize commands via environment variables, but the defaults work when `MESHCORE_TARGET` is set.

- Set the device target in `.env`:
  - `MESHCORE_TARGET=192.168.20.160`
- Optional overrides (advanced):
  - `MESHCORE_CLI` — path to the CLI binary (default `meshcore-cli`)
  - `MESH_INFO_COMMAND` — shell template to fetch node info; `{name}` placeholder is replaced
  - `MESH_CONTACTS_COMMAND`, `MESH_CONTACT_INFO_COMMAND` — custom collectors if you do not want the built-ins

Optional: Web Terminal (ttyd)
- A ttyd-based web console can be added to run interactive CLI sessions in the browser. It is not wired by default, but you can add a `ttyd` service and proxy it under `/terminal/` in Nginx if desired.
- The `meshcore/` directory contains a placeholder Dockerfile to host a custom CLI build if you clone it locally.

## Project Layout

- `frontend/` — Vue 3 + Vite + Tailwind SPA
- `backend/` — Django + DRF app with JWT and CORS
- `docker/nginx/` — Nginx Dockerfile and config
- `meshcore/` — Optional container scaffolding for meshcore-cli
- `docker-compose.yml` — Services and wiring for local/dev deployment

## Environment

Copy `.env.example` to `.env` and adjust as needed:
- Core: `PROJECT_NAME`, `ENV`
- Ports: `HTTP_PORT` (and `HTTPS_PORT` if you add TLS)
- Backend: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`
- CORS: `CORS_ALLOWED_ORIGINS` (comma-separated)
- Database: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`
- Device: `MESHCORE_TARGET` and optional `MESHCORE_CLI`
- Internal: `BACKEND_PORT` (defaults to 8000)

## Running (Docker)

- Build and start: `docker compose up -d --build`
- View logs: `docker compose logs -f backend` (or `db`, `nginx`, `collector`)
- Create admin user: `docker compose exec backend python manage.py createsuperuser`
- Run migrations/collectstatic happen automatically in the backend entrypoint.

HTTPS
- Provide certs and enable the 443 mapping in `docker-compose.yml`.
- Extend `docker/nginx/nginx.conf` to listen on 443 with TLS configuration.

## Running (Local Dev)

Backend
- Requirements: Python 3.11, PostgreSQL 15+
- Setup:
  - `cd backend`
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - Export env vars to point at your DB (or run Postgres via Docker).
  - `python manage.py migrate && python manage.py runserver 0.0.0.0:8000`

Frontend
- Requirements: Node.js 18+
- Setup:
  - `cd frontend`
  - `npm install`
  - `npm run dev`
- Ensure `CORS_ALLOWED_ORIGINS` includes the Vite dev server origin (e.g., `http://localhost:5173`).

## API Overview (JSON over REST)

Base path: `/api/v1/...` (Nginx forwards `/api/` to backend `/v1/`). Status codes: 200, 201, 400, 401, 403, 404.

Auth
- `POST /api/v1/auth/token/` — obtain JWT
- `POST /api/v1/auth/token/refresh/` — refresh access token

Health and Node
- `GET /api/v1/health/` — basic health
- `GET /api/v1/my-node/?name=NAME&max_age=SECONDS` — cached node info (force refresh with `max_age=0`)

Contacts and Telemetry
- `GET /api/v1/contacts/` — live contacts from CLI
- `GET /api/v1/contacts/latest/` — contacts with latest telemetry from DB
- `GET /api/v1/contact-info/?name=NAME` — on-demand single-node info

Messages
- `GET /api/v1/messages/?name=NAME|public_key=HEX[&limit=N]` — latest messages
- `POST /api/v1/messages/send/` — send a message `{ name|public_key, text, client_id? }`

Automations
- `GET /api/v1/automations/` — list rules
- `POST /api/v1/automations/` — create rule
- `GET|PUT|PATCH|DELETE /api/v1/automations/{id}/` — manage rule
- `POST /api/v1/automations/test/` — dry-run a message through rules

Connection
- `GET /api/v1/connection/status/` — whether an interactive session is up
- `POST /api/v1/connection/reconnect/` — try to start/restart interactive session

Settings: Collector
- `GET /api/v1/settings/collector/` — interval and flags
- `PUT /api/v1/settings/collector/` — update interval and flags

Settings: MQTT
- `GET /api/v1/settings/mqtt/` — `{ server, port, username, password_set, use_tls, default_community }`
- `PUT /api/v1/settings/mqtt/` — update settings; include `password` only when changing it
- `POST /api/v1/settings/mqtt/test/` — checks broker connectivity

Error shape
- Errors are returned as JSON with either `{ detail: "..." }` or `{ error: "..." }` depending on endpoint.

## Background Collector

A background loop collects contact info and telemetry at a configurable interval and syncs unread messages periodically.

- Service: `collector` (see `docker-compose.yml`)
- Command: `python manage.py run_contact_collector --min-interval 30 --debug`
- Tuning: controlled via `settings/collector` API (interval, request-status, request-telemetry)

You can also drive node info caching via cron:

```
docker compose exec backend python manage.py fetch_my_node --name JOST_DEV --max-age 0
```

## Development Guidelines

- Frontend: small, reusable components; prefer Tailwind utilities. Format with Prettier.
- Backend: keep serializers/viewsets separate from business logic; put logic under `services/` and utilities. Format with Black.
- Tests: Django TestCase and/or pytest are recommended. Run `python manage.py test` in `backend/` for basic coverage.

## Troubleshooting

- CLI cannot connect: ensure `MESHCORE_TARGET` points to your Wi‑Fi companion IP and the device is reachable from Docker network. Verify the firmware is running and your port (if non-default) is open.
- CORS errors in local dev: include your Vite dev origin in `CORS_ALLOWED_ORIGINS`.
- Database connection issues: confirm `POSTGRES_*` in `.env` and that the `db` service is healthy.
- Empty data in Dashboard: in DEBUG without a configured command, the backend uses built-in sample data; set `MESHCORE_TARGET` to get live values.

## Deployment

- Backend: Gunicorn behind Nginx (already configured in Docker images).
- Env: use `.env` for secrets/DB; never commit secrets.
- HTTPS: use Let’s Encrypt or your CA; configure TLS in Nginx and expose 443.
- Observability: logs are streamed to stdout; consider forwarding to your log stack.

## Notes

- This repository includes optional scaffolding for integrating `meshcore-cli`. If you bring your own build, point `MESHCORE_CLI` to it or place it in PATH.
- The Wi‑Fi companion firmware is external to this repo and must be compiled by you. Ensure Wi‑Fi credentials are embedded at compile time as shown above.


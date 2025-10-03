Entkoppelte/Headless SPA-Architektur: Vue 3 SPA + Django REST (DRF) Backend, JSON-REST, Nginx Reverse Proxy, optional Docker.

Überblick

- Architektur: Vue 3 Single Page App + Django REST API (DRF)
- Kommunikation: JSON über REST unter `/api/v1/...` (Nginx leitet `/api/` an das Backend weiter)
- Deployment: Nginx als Reverse Proxy, optional Docker-Compose

Frontend (Vue 3 + Tailwind)

- Verantwortlich für UI/UX, Routing (Vue Router), State (Pinia)
- Holt Daten via Axios von der REST-API
- Features: Dashboard (My Node), Devices/Contacts, Messages (Senden/Empfangen), Automation (Regeln), Settings (MQTT, Collector), Map, Responsive, Dark-Mode
- Build: `npm run build` (Output statisch via Nginx)

Backend (Django + DRF)

- Stellt REST-Endpunkte, Validierung, Business-Logik, DB-Zugriff (PostgreSQL empfohlen)
- Auth: JWT (djangorestframework-simplejwt) vorgesehen
- CORS: `django-cors-headers` für das Frontend
- Beispiel-Endpoints:
  - `GET /api/v1/health/`
  - `GET /api/v1/my-node/`
  - `GET /api/v1/contacts/latest/`
  - `GET /api/v1/messages/`, `POST /api/v1/messages/send/`
  - `GET|POST /api/v1/settings/collector/`
  - `GET|POST /api/v1/settings/mqtt/`, `POST /api/v1/settings/mqtt/test/`
  - `GET /api/v1/automations/`, `POST /api/v1/automations/`, `GET|PUT|PATCH|DELETE /api/v1/automations/{id}/`, `POST /api/v1/automations/test/`
  - `GET /api/v1/connection/status/`, `POST /api/v1/connection/reconnect/`

API & Fehler

- Versionierung: `/api/v1/...`
- Erwartete Statuscodes: 200, 201, 400, 401, 403, 404
- Einheitliche JSON-Fehlerstruktur (z. B. `{ detail: "..." }`)

Richtlinien

- Frontend: kleine, wiederverwendbare Komponenten; Tailwind-Utilities bevorzugen
- Backend: Serializer/ViewSets trennen; Logik in Services/Utils kapseln
- Code-Format: Prettier (JS), Black (Python); Tests mit pytest/Django TestCase

Deployment

- Backend: Django + Gunicorn hinter Nginx
- Env: `.env` für Secrets/DB und Meshcore-Target
- HTTPS: Let’s Encrypt Zertifikate

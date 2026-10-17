# PlanIT Control backend

Flask REST API with background jobs that pull live hazard data for 58 real power-plant job sites, score them, raise alerts, send 6 PM next-day briefings, and answer questions through a Claude-powered assistant. The full API contract is in [`../docs/API.md`](../docs/API.md).

## Setup

```bash
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt      # Windows
# .venv/bin/python -m pip install -r requirements.txt        # macOS / Linux
copy .env.example .env                                        # optional; defaults work for development
```

## Run

```bash
.venv\Scripts\python run.py        # development server: http://localhost:5000
```

On first start it creates the SQLite database (`instance/planit.db`), loads the 58 sites from `data/sites.csv`, creates the demo accounts **supervisor** and **crew** (password `planit-demo`, development only) and starts the background jobs. The first weather refresh runs a few seconds after startup.

Run the frontend next to it with `npm run dev` in `frontend/`, which proxies `/api` here. Alternatively, run `npm run build` once; this server then also serves the built app at `http://localhost:5000`.

Production: `python serve.py` (Waitress). See [`../docs/DEPLOY.md`](../docs/DEPLOY.md).

## Configuration

Settings come from environment variables or `backend/.env`; [`.env.example`](.env.example) lists them all. The ones you're most likely to set:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | session signing key (required in production) |
| `ANTHROPIC_API_KEY` | turns on the AI assistant (`POST /api/chat`) |
| `CONTACT_EMAIL` | sent in the User-Agent to public data APIs (NWS asks for one) |
| `SMTP_*`, `TWILIO_*` | real email / SMS; without them messages are only recorded in the outbox |
| `LIGHTNING_SOURCE` | `glm` (NOAA GOES satellites, ~1 MB/min) or `off` |
| `DEMO_TOOLS`, `SEED_DEMO_USERS` | demo accounts and the "simulate strike" button (on in development) |

## Commands

```bash
.venv\Scripts\python -m pytest                                   # 60 tests, no network needed
.venv\Scripts\flask --app run refresh                            # pull every data source once
.venv\Scripts\flask --app run briefings                          # send tomorrow's briefings now
.venv\Scripts\flask --app run create-supervisor                  # add a supervisor (use in production)
.venv\Scripts\python -I scripts/build_sites.py <eia860m.xlsx>    # rebuild data/sites.csv from EIA-860M
```

## How it works

```
Background jobs (app/jobs.py)                      REST API (app/api/)
  weather    Open-Meteo, hourly        ┐             auth, users, sites, alerts (+ SSE stream),
  NWS alerts api.weather.gov, 10 min   │             reports (+ photo uploads), briefings,
  rivers     USGS gauges, 30 min       ├─► Site row ─► settings, stats, notifications, chat, meta
  fires      NASA FIRMS, hourly        │   (JSON)        ▲
  wildlife   iNaturalist, 12 h         │      │          │
  lightning  NOAA GOES GLM, 60 s       ┘      ▼          │
                                  services/hazards.py ─► services/alert_engine.py ─► SSE + email/SMS
  briefings  every 5 min: 6 PM site-local ─► services/briefings.py ─► services/notify.py
```

- **Scoring** (`services/hazards.py`): rule-based and documented in [`../docs/API.md`](../docs/API.md#how-scores-are-computed). Every site response carries `scoring.method` (`rule-based`); the ML model is paused until its training data is settled and can replace `combine()` later.
- **Alerts** (`services/alert_engine.py`): one active alert per site and rule; lightning alerts clear themselves 30 minutes after the last strike within 10 miles.
- **Writes** go through one lock (`services/ingest.py`) with SQLite in WAL mode; reads happen first, so write transactions stay short.

## Layout

```
backend/
├── run.py, serve.py        development and production servers
├── config.py               settings (env vars / .env)
├── requirements.txt
├── data/sites.csv          the 58 job sites (from EIA-860M)
├── scripts/build_sites.py  rebuilds data/sites.csv
├── app/
│   ├── __init__.py         create_app(), error handlers
│   ├── models.py           User, Site, LightningStrike, Alert, AlertAck, HazardReport,
│   │                       Briefing, Setting, Notification
│   ├── api/                one blueprint per resource + spa.py (serves frontend/dist)
│   ├── services/           data-source clients, scoring, alerts, briefings, notify, assistant
│   ├── jobs.py, cli.py, seed.py, security.py, settings_store.py
└── tests/                  pytest suite
```

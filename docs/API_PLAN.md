# PlanIT Control REST API plan

This is the contract between the React frontend (`frontend/`) and the Flask backend (`backend/`). It is a plan only: endpoints marked **PLANNED** are not implemented yet. The frontend already calls every endpoint below through `frontend/src/api/`. Until the backend exists, those calls return mock data (`VITE_USE_MOCKS=true`).

- Base URL: `/api` (the Vite dev server proxies this to `http://localhost:5000`)
- Format: JSON in both directions, except report uploads, which use `multipart/form-data`
- Auth: Flask-Login session cookie, so the frontend sends `credentials: 'include'`
- Errors: `{ "message": "..." }` with an HTTP status (400, 401, 403, 404, 409)
- Frontend references: endpoint paths are in `frontend/src/api/endpoints.js`, and every call site is marked `REST API PLACEHOLDER`

## Roles and permissions

There are two roles, and **no admin role**. Supervisors hold every management privilege.

| Capability | Crew | Supervisor |
|---|:-:|:-:|
| View sites, alerts and briefings | ✓ | ✓ |
| Report hazards (photo + map pin) | ✓ | ✓ |
| Use the AI assistant | ✓ | ✓ |
| PlanIt Dashboard (ranked risk map) | | ✓ |
| Manage users and roles | | ✓ |
| Add, edit, pause or delete sites | | ✓ |
| Edit alert rules and briefing settings; send briefings now | | ✓ |
| Moderate hazard reports | | ✓ |

The "Who" column in the tables below uses **Any** (any signed-in user) or **Supervisor**. Always check permissions on the server from `current_user.role`, never from anything the client sends.

**Changes to the existing backend code:**

1. Replace `User.is_admin` with `role = db.Column(db.String(20), nullable=False, default='crew')`. Migrate existing rows with `is_admin=True` to `role='supervisor'`.
2. Replace `admin_required()` with `supervisor_required()`, which checks `current_user.role == 'supervisor'`.
3. Remove the `/api/admins` blueprint. Listing and creating users moves to `GET`/`POST /api/users`. The existing `/api/users/<id>` routes already allow "self or privileged user", so switch their `is_admin` checks to the supervisor check. Only supervisors may change `role`; return 403 if anyone else sends it.
4. `/auth/register` always creates a crew account. Supervisors are created with `POST /users` or promoted with `PUT /users/:id { "role": "supervisor" }`.

## URL conventions (keep these when implementing)

- Plural, lowercase kebab-case resource names: `/sites`, `/settings/alert-rules`
- No role prefixes in paths (no `/admin/...`). The same path serves everyone, and the role decides what is allowed.
- IDs go in the path and are URL-encoded: `/sites/turkey-point`
- Site IDs are readable slugs (`^[a-z0-9]+(-[a-z0-9]+)*$`) generated from the plant name, e.g. "Big Cajun II" → `big-cajun-ii`, with `-2`, `-3`… added on collisions. The same ID appears in the browser URL (`/sites/big-cajun-ii`), so never use database integers for sites.
- Filters go in query parameters, never in the path: `/alerts?active=true&siteId=turkey-point`. The frontend leaves out empty filters rather than sending `?siteId=`.
- One path, different verbs: `GET /sites` lists, `POST /sites` creates.
- Actions on one resource are sub-paths: `POST /alerts/:id/ack`
- Unknown resources return **404** with `{ "message": "..." }`. The frontend turns that into a "not found" page.

## Frontend routes → API calls

Page URLs mirror the API resources they read. All page URLs are defined in `frontend/src/routes.js`.

| Page URL | Page | Who | API calls |
|---|---|---|---|
| `/login?next=/manage/users` | Sign in | Anyone | `POST /auth/login` |
| `/` | Redirects by role (crew → `/sites`, supervisor → `/dashboard`) | Any | none |
| `/dashboard?decision=no-go` | PlanIt Dashboard | Supervisor | `GET /sites`, `GET /alerts?active=true` |
| `/sites?q=florida` | Site list | Any | `GET /sites` |
| `/sites/:siteId` | Site risk picture | Any | `GET /sites/:siteId`, `GET /sites/:siteId/forecast`, `GET /sites/:siteId/lightning`, `GET /alerts?active=true&siteId=`, `GET /reports?siteId=` |
| `/alerts?type=lightning` | Alert feed | Any | `GET /alerts?active=true`, `POST /alerts/:id/ack`, `GET /alerts/stream` |
| `/reports/new?site=:siteId` | Crew hazard report | Any | `GET /sites`, `POST /reports` |
| `/briefings?q=texas` | Next-day briefings | Any | `GET /briefings` |
| `/manage/overview` | Manage › Overview | Supervisor | `GET /stats`, `GET /sites` |
| `/manage/users` | Manage › Users | Supervisor | `GET/POST /users`, `PUT/DELETE /users/:id` |
| `/manage/sites?q=entergy` | Manage › Sites | Supervisor | `GET /sites?includeInactive=true`, `POST /sites`, `PUT/DELETE /sites/:id` |
| `/manage/alert-rules` | Manage › Alert rules | Supervisor | `GET/PUT /settings/alert-rules` |
| `/manage/reports?status=open` | Manage › Hazard reports | Supervisor | `GET /reports`, `PATCH /reports/:id` |
| `/manage/briefings` | Manage › Briefings | Supervisor | `GET/PUT /settings/briefings`, `POST /briefings` |
| Every signed-in page | AI assistant (floating chat) | Any | `POST /chat` (+ `GET /sites/:siteId` for the site name) |

**Production hosting:** this is a single-page app, so the web server must serve `index.html` for every non-`/api` path. Otherwise reloading `/manage/users` returns 404. With Flask, add a catch-all route that returns `frontend/dist/index.html`.

---

## 1. Auth (`/api/auth`)

| Method | Path | Status | Who | Body | Response |
|---|---|---|---|---|---|
| POST | `/auth/register` | EXISTS | Anyone | `{ username, email, password }` | `{ message }` (creates a crew account) |
| POST | `/auth/login` | EXISTS (change) | Anyone | `{ username, password }` | `{ message, user }`: **add `user`** |
| POST | `/auth/logout` | EXISTS | Any | none | `{ message }` |
| GET | `/auth/me` | PLANNED | Any | none | `{ user }`, or 401 |

`User` = `{ id, username, email, role: "crew" | "supervisor" }`

## 2. Users (`/api/users`)

| Method | Path | Status | Who | Body | Response |
|---|---|---|---|---|---|
| GET | `/users` | PLANNED | Supervisor | none | `{ users: User[] }` |
| POST | `/users` | PLANNED | Supervisor | `{ username, email, password, role }` | `{ user }` (409 if the username or email exists) |
| GET | `/users/:id` | EXISTS | Self or supervisor | none | `User` |
| PUT | `/users/:id` | EXISTS (add `role`) | Self or supervisor; `role` is supervisor-only | `{ username?, email?, password?, role? }` | `{ message }` |
| DELETE | `/users/:id` | EXISTS | Self or supervisor | none | `{ message }` |

## 3. Sites (`/api/sites`)

| Method | Path | Status | Who | Body | Response |
|---|---|---|---|---|---|
| GET | `/sites` | PLANNED | Any (`includeInactive`: supervisor) | `?includeInactive=true` | `{ sites: Site[] }` |
| POST | `/sites` | PLANNED | Supervisor | `{ name, state, lat, lng, plantType, utility, waterway, timezone }` | `{ site }` (server generates the slug `id`) |
| GET | `/sites/:id` | PLANNED | Any | none | `{ site: Site }` |
| PUT | `/sites/:id` | PLANNED | Supervisor | any Site fields, including `active` | `{ message }` |
| DELETE | `/sites/:id` | PLANNED | Supervisor | none | `{ message }` |
| GET | `/sites/:id/forecast` | PLANNED | Any | none | `{ forecast: [{ date, hazardIndex, topHazard }] }`, 7 site-local dates starting tomorrow |
| GET | `/sites/:id/lightning` | PLANNED | Any | none | `{ lastStrikeAt, distanceMiles }`: latest strike within the configured radius, or `null`s |

```jsonc
// Site
{
  "id": "turkey-point",
  "name": "Turkey Point",
  "state": "FL",
  "lat": 25.4356, "lng": -80.3308,
  "plantType": "Nuclear / Gas",
  "utility": "Florida Power & Light",
  "timezone": "America/New_York",       // drives the 6 PM local briefing and "tomorrow"
  "waterway": "Biscayne Bay",           // null if not on a river or coast
  "active": true,
  "hazardIndex": 8.1,                   // ML model output, 0-10
  "hazards": { "heat": 9.2, "lightning": 7.4, "flooding": 5.1, "wildfire": 1.3,
               "soil": 7.8, "wildlife": 8.0, "wind": 3.9 },
  "conditions": { "tempF": 94, "heatIndexF": 111, "humidityPct": 78, "windMph": 12,
                  "precip24hIn": 1.9, "soilMoisturePct": 69, "lightningStrikes1h": 22,
                  "riverStageFt": 19.2, "fireWeatherIndex": 11.7 },
  "drivers": ["Heat index 111°F by midday", "..."],  // plain-language reasons
  "updatedAt": "2026-10-16T13:45:00Z"
}
```

## 4. Alerts (`/api/alerts`)

| Method | Path | Status | Who | Body / query | Response |
|---|---|---|---|---|---|
| GET | `/alerts` | PLANNED | Any | `?active=true&siteId=` | `{ alerts: Alert[] }` |
| POST | `/alerts/:id/ack` | PLANNED | Any | none | `{ alert }` |
| GET | `/alerts/stream` | PLANNED | Any | Server-Sent Events | `data: Alert` for each new alert |

`Alert` = `{ id, siteId, siteName, type, severity: "stop-work" | "warning" | "info", title, message, createdAt, active, acknowledged }`

Until `/alerts/stream` exists, the frontend polls `/alerts` every 15–30 s.

## 5. Crew hazard reports (`/api/reports`)

| Method | Path | Status | Who | Body / query | Response |
|---|---|---|---|---|---|
| GET | `/reports` | PLANNED | Any | `?siteId=&status=` | `{ reports: Report[] }` |
| POST | `/reports` | PLANNED | Any | multipart: `siteId, type, description, lat, lng, photo` | `{ report }` |
| PATCH | `/reports/:id` | PLANNED | Supervisor | `{ status }` | `{ report }` |

`Report` = `{ id, siteId, type, description, lat, lng, photoUrl, reportedBy, createdAt, status: "open" | "verified" | "resolved" | "dismissed" }`

Store photos under `backend/uploads/` (or S3) and serve them by URL. A new report should also be pushed to that site's crew through the alert stream.

## 6. Briefings (`/api/briefings`)

| Method | Path | Status | Who | Body | Response |
|---|---|---|---|---|---|
| GET | `/briefings` | PLANNED | Any | `?date=YYYY-MM-DD` | `{ briefings: Briefing[] }`, the latest for each active site |
| POST | `/briefings` | PLANNED | Supervisor | `{ siteIds? }` (omit for all active sites) | `{ sent }`: generates and sends briefings now |
| GET | `/briefings/:siteId` | PLANNED | Any | none | `{ briefing }` |

`Briefing` = `{ siteId, siteName, state, timezone, forDate, hazardIndex, decision: "GO" | "CAUTION" | "NO-GO", summary, topHazards: [{ key, score, control }] }`

## 7. Settings (`/api/settings`)

Single configuration resources read by the backend jobs.

| Method | Path | Status | Who | Body | Response |
|---|---|---|---|---|---|
| GET | `/settings/alert-rules` | PLANNED | Any | none | `{ rules }` |
| PUT | `/settings/alert-rules` | PLANNED | Supervisor | `{ rules }` | `{ rules }` |
| GET | `/settings/briefings` | PLANNED | Supervisor | none | `{ settings }` |
| PUT | `/settings/briefings` | PLANNED | Supervisor | `{ settings }` | `{ settings }` |

```jsonc
// rules (defaults come from the brief)
{ "lightningRadiusMiles": 10, "lightningAllClearMinutes": 30, "floodRainInches": 2,
  "heatIndexF": 105, "windMph": 35, "hazardIndexAlert": 7.5 }

// settings
{ "enabled": true, "localTime": "18:00",
  "channels": { "email": true, "sms": true, "push": true },
  "recipients": ["crew", "supervisor"] }
```

## 8. Stats (`/api/stats`)

| Method | Path | Status | Who | Response |
|---|---|---|---|---|
| GET | `/stats` | PLANNED | Supervisor | `{ stats: { sites, noGoSites, activeAlerts, openReports, users } }` |

## 9. AI assistant (`/api/chat`)

A floating chat on every signed-in page lets crews and supervisors ask about site risk, alerts, safety rules, tomorrow's briefing and how to report hazards. The browser never calls the language model. Flask holds the API key, adds live data from the database, calls Claude and returns the reply.

| Method | Path | Status | Who | Body | Response |
|---|---|---|---|---|---|
| POST | `/chat` | PLANNED | Any | `{ messages: [{ role: "user" \| "assistant", content }], siteId? }` | `{ reply: { role: "assistant", content } }` |

`siteId` is the site the user is looking at (`/sites/:siteId` or `/reports/new?site=`), so answers can use that site's data.

**Server steps:**

1. **Validate** (400 on failure): 1–20 messages, each with `role` `user` or `assistant` and a `content` string of 1–2,000 characters, with the first message from the user. `siteId`, if present, must be a valid slug. The frontend already trims to the last 20 turns.
2. **Build context from the database**, never from the client: the user's role (from the session), the `siteId` site's hazard picture, lightning status, active alerts and tomorrow's briefing, the 5 riskiest sites, and the alert rules.
3. **Call Claude** with the Anthropic Python SDK (snippet below). Put the API key in `ANTHROPIC_API_KEY` in the server's environment only. Never put it in a `VITE_` variable: Vite bundles those into the public JavaScript.
4. **Return the text reply.** Rate-limit per user (e.g. 20 requests a minute with Flask-Limiter).

**System prompt outline.** Put the fixed instructions first and the per-request data last, so a future prompt cache can reuse the fixed part:

```text
You are PlanIT Assistant, a safety assistant for utility field crews and supervisors.
- Answer from the live site data below. If something isn't in it, say you don't know.
- Never say it is safe to work while a stop-work alert or lightning countdown is active.
- For injuries or emergencies, tell them to call 911 first, then their supervisor.
- Reply in plain text: short sentences and "•" bullets, no markdown. People read this on phones in the field.

<site_data>{ JSON: user role, current site, active alerts, rules, top 5 riskiest sites }</site_data>
```

**Flask sketch** (`backend/app/chat.py`, registered with `url_prefix="/api"`):

```python
import anthropic
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

chat_bp = Blueprint("chat", __name__)
client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the server environment


@chat_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    data = request.get_json(silent=True) or {}
    messages = validate_messages(data.get("messages"))             # step 1: raises -> 400
    system = build_system_prompt(current_user, data.get("siteId"))  # step 2: data from the DB

    try:
        response = client.beta.messages.create(
            model="claude-opus-5-5",
            max_tokens=16000,
            output_config={"effort": "medium"},  # try "low" if replies feel slow
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # if a safety check declines, re-run on a fallback model
            system=system,
            messages=messages,
        )
    except anthropic.RateLimitError:
        return jsonify(message="The assistant is busy. Try again in a minute."), 503
    except anthropic.APIStatusError:
        return jsonify(message="The assistant is unavailable right now."), 502
    except anthropic.APIConnectionError:
        return jsonify(message="Can't reach the assistant service."), 502

    if response.stop_reason == "refusal":
        content = "I can't help with that one. Please ask your supervisor."
    else:
        # The reply can include thinking blocks; keep only the text blocks.
        content = "".join(block.text for block in response.content if block.type == "text")
    return jsonify(reply={"role": "assistant", "content": content})
```

**Later upgrades (optional):**

- Streaming: `client.messages.stream(...)` forwarded as Server-Sent Events, so long answers appear word by word.
- Tool use: let the model call `get_site_status`, `list_riskiest_sites` and `get_active_alerts` instead of receiving all data up front.

---

## 10. Backend jobs (not HTTP endpoints)

| Job | Schedule | Does |
|---|---|---|
| Conditions ingest | every 5–10 min | Pull weather, heat index, precipitation, soil moisture, river stage and fire weather for every active site, then save a snapshot |
| Lightning monitor | real-time / every 1 min | Raise or refresh a **stop-work** alert for any strike within `lightningRadiusMiles`. Each new strike resets `lastStrikeAt`, and the alert clears `lightningAllClearMinutes` after the last strike |
| Flood monitor | hourly + 6 AM | Raise a **flood-risk warning** for sites with a `waterway` after overnight rain ≥ `floodRainInches` or a rising river gauge |
| Hazard scoring | after each ingest | Run the ML model, which writes `hazards`, `hazardIndex`, `drivers` and the 7-day forecast |
| Next-day briefing | every 15 min | For each site where local time has just passed `localTime` (18:00), build tomorrow's briefing (dates in the site's time zone) and send it on the enabled channels |

Suggested tooling: APScheduler (or Celery beat), with SSE pushes through Flask's streaming responses.

## 11. Suggested data sources

- Sites: EIA-860M (plant coordinates, utility, county, plant type)
- Weather / heat / precipitation: NWS API (`api.weather.gov`), Open-Meteo
- Lightning: a commercial feed such as Xweather or Earth Networks; NOAA GLM as a fallback
- Flooding: USGS Water Services (river gauges), NOAA Tides & Currents, FEMA NFHL flood zones, USACE National Levee Database
- Wildfire: NASA FIRMS, NIFC
- Soil moisture: NASA SMAP, or the Open-Meteo soil moisture fields
- ML training labels: NOAA Storm Events Database, Iowa Environmental Mesonet (NWS warnings archive), OSHA Severe Injury Reports

## 12. Planned backend additions

New Python packages for `backend/requirements.txt` (not added yet):

```
anthropic         # AI assistant: Claude API (POST /api/chat)
Flask-Limiter     # per-user rate limit on /api/chat
requests          # pull external hazard data
APScheduler       # ingest / monitor / 6 PM briefing jobs
pandas            # feature engineering
scikit-learn      # hazard-index model (e.g. gradient boosting regressor)
joblib            # save and load the trained model
```

Bug in the existing code to fix during implementation: `backend/app/__init__.py` uses `jsonify` in `unauthorized()` but never imports it.

New models: `Site`, `ConditionSnapshot`, `HazardScore`, `Alert`, `HazardReport`, `AlertRule`, `BriefingSetting`, `Briefing`.

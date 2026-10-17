# PlanIT Control REST API

The contract between the React frontend (`frontend/`) and the Flask backend (`backend/`). Everything below is implemented in `backend/app/api/`; the frontend calls it through `frontend/src/api/` (every call site is marked `REST API PLACEHOLDER`, and all paths live in `frontend/src/api/endpoints.js`).

- Base URL: `/api`. The Vite dev server proxies it to `http://localhost:5000`; in production Flask serves the built frontend and the API on one port.
- Format: JSON in both directions, except report uploads (`multipart/form-data`).
- Auth: Flask-Login session cookie (`HttpOnly`, `SameSite=Lax`, `Secure` in production). The frontend sends `credentials: 'include'`.
- Errors: `{ "message": "..." }` with an HTTP status (400, 401, 403, 404, 409, 413, 429, 502, 503).

## Roles and permissions

Two roles and **no admin role**. Supervisors hold every management privilege.

| Capability | Crew | Supervisor |
|---|:-:|:-:|
| View sites, alerts and briefings | ✓ | ✓ |
| Report hazards (photo + map pin) | ✓ | ✓ |
| Use the AI assistant | ✓ | ✓ |
| PlanIt Dashboard (ranked risk map) | | ✓ |
| Manage users and roles | | ✓ |
| Add, edit, pause or delete sites | | ✓ |
| Edit alert rules and briefing settings; send briefings now | | ✓ |
| Moderate hazard reports; read the notification outbox | | ✓ |

Permissions are checked on the server from `current_user.role` (`supervisor_required` in `backend/app/security.py`). Self-registration creates crew accounts; there must always be at least one supervisor (demoting or deleting the last one returns 409).

## URL conventions

- Plural, lowercase kebab-case resources: `/sites`, `/settings/alert-rules`. No role prefixes such as `/admin`.
- IDs are path segments, URL-encoded: `/sites/turkey-point`. Site IDs are readable slugs generated from the plant name (`Big Cajun II` → `big-cajun-ii`, with `-2`, `-3` on collisions); the same ID appears in browser URLs.
- Filters are query parameters (`/alerts?active=true&siteId=turkey-point`); empty filters are omitted.
- One path, different verbs: `GET /sites` lists, `POST /sites` creates. Actions on one resource are sub-paths: `POST /alerts/:id/ack`.
- Unknown resources return 404 JSON; the frontend shows its "not found" page.

## Frontend routes → API calls

| Page URL | Page | Who | API calls |
|---|---|---|---|
| `/login?next=/manage/users` | Sign in | Anyone | `GET /meta`, `POST /auth/login` |
| `/` | Redirect by role (crew → `/sites`, supervisor → `/dashboard`) | Any | none |
| `/dashboard?decision=no-go` | PlanIt Dashboard | Supervisor | `GET /sites`, `GET /alerts?active=true` |
| `/sites?q=florida` | Site list | Any | `GET /sites` |
| `/sites/:siteId` | Site risk picture | Any | `GET /sites/:siteId`, `/forecast`, `/lightning`, `GET /alerts?active=true&siteId=`, `GET /reports?siteId=` |
| `/alerts?type=lightning` | Alert feed | Any | `GET /alerts?active=true`, `POST /alerts/:id/ack`, `GET /alerts/stream` |
| `/reports/new?site=:siteId` | Crew hazard report | Any | `GET /sites`, `POST /reports` |
| `/briefings?q=texas` | Next-day briefings | Any | `GET /briefings` |
| `/manage/overview` | Manage › Overview | Supervisor | `GET /stats`, `GET /sites` |
| `/manage/users` | Manage › Users | Supervisor | `GET/POST /users`, `PUT/DELETE /users/:id` |
| `/manage/sites?q=entergy` | Manage › Sites | Supervisor | `GET /sites?includeInactive=true`, `POST /sites`, `PUT/DELETE /sites/:id` |
| `/manage/alert-rules` | Manage › Alert rules | Supervisor | `GET/PUT /settings/alert-rules` |
| `/manage/reports?status=open` | Manage › Hazard reports | Supervisor | `GET /reports`, `PATCH /reports/:id` |
| `/manage/briefings` | Manage › Briefings | Supervisor | `GET/PUT /settings/briefings`, `POST /briefings`, `GET /notifications` |
| Every signed-in page | AI assistant (floating chat) | Any | `POST /chat` (+ `GET /sites/:siteId` for the site name) |

---

## 1. Auth

| Method | Path | Who | Body | Response |
|---|---|---|---|---|
| POST | `/auth/register` | Anyone | `{ username, email, password }` | 201 `{ message, user }` (crew account) |
| POST | `/auth/login` | Anyone (10/min per IP) | `{ username, password }` | `{ message, user }` |
| POST | `/auth/logout` | Any | none | `{ message }` |
| GET | `/auth/me` | Any | none | `{ user }`, or 401 |

`User` = `{ id, username, email, role: "crew" | "supervisor", phone }`. Usernames are 3-64 letters/digits/`._-`; passwords at least 8 characters; `phone` (optional, for SMS) in E.164 format.

## 2. Users

| Method | Path | Who | Body | Response |
|---|---|---|---|---|
| GET | `/users` | Supervisor | none | `{ users }` |
| POST | `/users` | Supervisor | `{ username, email, password, role, phone? }` | 201 `{ user }`, 409 on duplicates |
| GET | `/users/:id` | Self or supervisor | none | `User` |
| PUT | `/users/:id` | Self or supervisor; `role` supervisor-only | `{ username?, email?, password?, role?, phone? }` | `{ message, user }` |
| DELETE | `/users/:id` | Self or supervisor | none | `{ message }` |

## 3. Sites

| Method | Path | Who | Body / query | Response |
|---|---|---|---|---|
| GET | `/sites` | Any (`includeInactive` supervisor) | `?includeInactive=true` | `{ sites: Site[] }` |
| POST | `/sites` | Supervisor | `{ name, state, county?, lat, lng, plantType, utility, waterway, timezone }` | 201 `{ site }` |
| GET | `/sites/:id` | Any | none | `{ site }` (404 if unknown or paused) |
| PUT | `/sites/:id` | Supervisor | any editable field, including `active` | `{ message, site }` |
| DELETE | `/sites/:id` | Supervisor | none | `{ message }` |
| GET | `/sites/:id/forecast` | Any | none | `{ forecast: [{ date, hazardIndex, topHazard }] }`, 7 site-local dates from tomorrow |
| GET | `/sites/:id/lightning` | Any | none | `{ lastStrikeAt, distanceMiles, strikesLastHour }` (latest strike within the stop-work radius) |
| POST | `/sites/:id/lightning/simulate` | Supervisor, `DEMO_TOOLS` on | none | same as above, after recording a strike 3 mi away |

```jsonc
// Site
{
  "id": "turkey-point", "eiaPlantId": 621, "name": "Turkey Point", "eiaName": "Turkey Point",
  "state": "FL", "county": "Miami Dade", "lat": 25.4356, "lng": -80.3308,
  "utility": "Florida Power & Light Co", "plantType": "Nuclear / Natural Gas", "capacityMw": 2978.4,
  "timezone": "America/New_York",   // drives the 6 PM local briefing and "tomorrow"
  "waterway": "Biscayne Bay",       // null if not on a river or coast
  "active": true,
  "hazardIndex": 3.4,               // 0-10, see "How scores are computed"
  "hazards": { "heat": 3.8, "lightning": 0.6, "flooding": 0, "wildfire": 0, "soil": 1.0, "wildlife": 3, "wind": 0.8 },
  "conditions": { "tempF": 86, "heatIndexF": 96, "humidityPct": 70, "windMph": 9, "windGustMph": 14,
                  "precip24hIn": 0, "soilMoisturePct": 20, "lightningStrikes1h": 0, "riverStageFt": 0.3,
                  "riverChange24hFt": 0, "nearestFireMiles": 61, "wildlifeSightings30d": 2, "nwsAlerts": 1,
                  "modelRiskPct": 12 },   // the ML model's chance of a reported hazardous event nearby today
  "drivers": ["Heat index up to 97°F in the next 12 h", "..."],   // plain-language reasons
  "updatedAt": "2026-10-17T16:05:00Z",
  "scoring": { "method": "ml+rules", "label": "ML model (NOAA storm history) plus safety rules",
               "model": { "fittedAt": "2026-10-17T18:03:41Z", "years": [2023, 2024, 2025], "auc": 0.854, "rulesAuc": 0.757 } }
}
```

## 4. Alerts

| Method | Path | Who | Query | Response |
|---|---|---|---|---|
| GET | `/alerts` | Any | `?active=true&siteId=` | `{ alerts }`, stop-work first, then newest |
| POST | `/alerts/:id/ack` | Any | none | `{ alert }` (acknowledgement is per user) |
| GET | `/alerts/stream` | Any | Server-Sent Events | `data: { type: "alert" \| "report" \| "briefing", ... }` |

`Alert` = `{ id, siteId, siteName, type, severity: "stop-work" | "warning" | "info", title, message, createdAt, updatedAt, active, acknowledged }`. `type` is one of the hazard categories (`heat`, `lightning`, `flooding`, `wildfire`, `soil`, `wildlife`, `wind`).

The browser keeps the stream open only while the tab is visible (browsers allow about six HTTP/1.1 connections per site across all tabs) and polls `/alerts` every 15-30 s as a fallback.

## 5. Crew hazard reports

| Method | Path | Who | Body / query | Response |
|---|---|---|---|---|
| GET | `/reports` | Any | `?siteId=&status=` | `{ reports }` |
| POST | `/reports` | Any | multipart: `siteId, type, description, lat, lng, photo?` | 201 `{ report }` |
| PATCH | `/reports/:id` | Supervisor | `{ status }` | `{ report }` |
| GET | `/uploads/:filename` | Any | none | the photo |

`Report` = `{ id, siteId, type, description, lat, lng, photoUrl, reportedBy, createdAt, status: "open" | "verified" | "resolved" | "dismissed" }`. Photos must be JPEG, PNG, GIF or WebP (checked by content, not file name), at most `MAX_UPLOAD_MB` (10 MB); they are stored under random names in `UPLOAD_FOLDER`. Crew wildlife reports from the last 7 days raise the site's wildlife score.

## 6. Briefings

| Method | Path | Who | Body | Response |
|---|---|---|---|---|
| GET | `/briefings` | Any | none | `{ briefings }`: tomorrow's briefing per active site (`generated: false` = live preview) |
| GET | `/briefings/:siteId` | Any | none | `{ briefing }` |
| POST | `/briefings` | Supervisor | `{ siteIds? }` (omit for all) | `{ sent }`: generate and send now |

`Briefing` = `{ siteId, siteName, state, timezone, forDate, hazardIndex, decision: "GO" | "CAUTION" | "NO-GO", summary, topHazards: [{ key, score, control }], generated }`.

## 7. Settings

| Method | Path | Who | Body | Response |
|---|---|---|---|---|
| GET | `/settings/alert-rules` | Any | none | `{ rules }` |
| PUT | `/settings/alert-rules` | Supervisor | `{ rules }` | `{ rules }` |
| GET | `/settings/briefings` | Supervisor | none | `{ settings }` |
| PUT | `/settings/briefings` | Supervisor | `{ settings }` | `{ settings }` |

```jsonc
// rules (defaults from the brief; allowed ranges are validated)
{ "lightningRadiusMiles": 10, "lightningAllClearMinutes": 30, "floodRainInches": 2,
  "heatIndexF": 105, "windMph": 35, "hazardIndexAlert": 7.5 }
// settings
{ "enabled": true, "localTime": "18:00", "channels": { "email": true, "sms": true, "push": true },
  "recipients": ["crew", "supervisor"] }
```

## 8. Stats, notifications, meta

| Method | Path | Who | Response |
|---|---|---|---|
| GET | `/stats` | Supervisor | `{ stats: { sites, noGoSites, activeAlerts, openReports, users } }` |
| GET | `/notifications?limit=20` | Supervisor | `{ notifications: [{ id, createdAt, channel, recipient, subject, body, status: "sent" \| "logged" \| "failed", error }] }` |
| GET | `/meta` | Anyone | `{ api, demoTools, demoAccounts, assistant, lightningSource, scoring }` (the frontend uses it to detect the backend) |

## 9. AI assistant

| Method | Path | Who | Body | Response |
|---|---|---|---|---|
| POST | `/chat` | Any (20/min per user) | `{ messages: [{ role: "user" \| "assistant", content }], siteId? }` | `{ reply: { role: "assistant", content } }` |

Implemented in `backend/app/services/assistant.py`. The server validates the conversation (1-20 messages, first from the user, each 1-2,000 characters), builds context from the database (user role, alert rules, five riskiest sites, and for `siteId` its scores, conditions, active alerts, lightning status and tomorrow's briefing) and calls Claude (`claude-opus-5-5`, configurable with `CLAUDE_MODEL`) through the Anthropic Python SDK with `fallbacks: "default"`, which re-runs a request on Anthropic's fallback model if a safety check declines it. Replies are plain text. Without `ANTHROPIC_API_KEY` the endpoint returns 503 with a message saying so; rate limits and outages return 503/502.

---

## How scores are computed

`backend/app/services/hazards.py` scores each hazard with transparent rules, and an ML model (below) adds an estimate learned from NOAA storm history. Each hazard maps a measured value onto 0-10 (values in between are interpolated):

| Hazard | Input | Breakpoints (value → score) |
|---|---|---|
| Heat | highest heat index in the next 12 h | 80°F → 0, 90 → 3, 103 → 6, 115 → 9, 125 → 10 (NWS categories) |
| Lightning | GOES strikes within the radius in the all-clear window → 10; any within 30 mi in the last hour → 7; otherwise storm energy (CAPE) and thunderstorm forecasts | CAPE 1,000 J/kg → 2, 2,500 → 4, 4,000 → 5.5; thunderstorm forecast → 5 |
| Flooding | rain in the last 24 h; river gauge rise for waterway sites | 0.5" → 2, 1" → 3.5, 2" → 6, 4" → 9; rise 1 ft → 2, 3 → 6, 6 → 9 |
| Wildfire | nearest satellite fire detection; dry + windy | ≤5 mi → 9, ≤10 → 7, ≤25 → 4; humidity < 20% with gusts ≥ 25 mph adds 2 |
| Soil saturation | soil moisture 3-9 cm | 0.25 m³/m³ → 3, 0.35 → 6, 0.42 → 8, 0.48 → 10 |
| Wildlife | dangerous-species sightings within 10 mi (30 days); crew wildlife reports (7 days) | 1 → 3, 3 → 5, 10 → 6.5; any crew report → 7 |
| Wind | strongest gust in the next 12 h | 25 mph → 3, 35 → 6, 45 → 8, 55 → 10 |

Official NWS alerts set minimum scores (e.g. Tornado Warning 10, Flash Flood Warning 8.5, Severe Thunderstorm Warning 8, Extreme Heat Warning 8, Heat Advisory 6). The **hazard index** is `0.6 × worst + 0.25 × second + 0.15 × average`, never below an active stop-work (8) or NWS minimum. Bands: ≤2.5 Low (GO), ≤5 Moderate (GO), ≤7.5 High (CAUTION), above 7.5 Extreme (NO-GO). The 7-day forecast applies the same breakpoints to Open-Meteo's daily forecast.

**ML hazard model** (`services/hazard_model.py`, fitted by `ml/fit_hazard_model.py`): a logistic regression that estimates the chance that NOAA's [Storm Events database](https://www.ncdc.noaa.gov/stormevents/) records a thunderstorm-wind, lightning, hail, tornado, flood, heat, high-wind, tropical-storm or wildfire event within 25 miles of the site, or in its NWS forecast zone or county, on a given day. Its inputs are that day's weather, taken from the same Open-Meteo daily values the forecast provides (highest heat index, rain and hours of rain, rain over the previous 3 days, strongest gust and wind, lowest humidity), plus the time of year and the site's location. It was fitted on 2023-2025 at the 58 sites (63,568 site-days, 4.3% of them with a qualifying report). Fitted on 2023-2024 and checked on 2025, it ranked hazardous days above calm ones 85% of the time (ROC AUC 0.854), against 76% (0.757) for the rule-based index on the same weather, and its probabilities beat always guessing the average (Brier score 0.032 vs 0.036). The coefficients and these checks are in `ml/hazard_model.json`.

The model's index is 10 × that chance (so 7.5, the NO-GO line, means a 75% chance of a reported event nearby). The site's **hazard index is the higher of the model and the rules**, so the model can raise the index but never lower what a stop-work, an NWS warning or another rule requires. The 7-day forecast and the 6 PM briefings use the same combination, and **ML model risk today** (`conditions.modelRiskPct`) shows the model's own estimate. Refit with `python -m ml.fit_hazard_model` from `backend/` (it writes `ml/hazard_model.json`); without that file, scoring falls back to the rules alone and `scoring.method` is `rule-based`.

## Alert rules

| Rule | Condition (thresholds from `/settings/alert-rules`) | Severity |
|---|---|---|
| Lightning | strike within `lightningRadiusMiles` in the last `lightningAllClearMinutes` (clears automatically; each strike restarts the countdown) | stop-work |
| Flood risk | waterway site with ≥ `floodRainInches` of rain in 24 h or the gauge up ≥ 2 ft | warning |
| Extreme heat | heat index ≥ `heatIndexF` in the next 12 h | warning |
| High wind | gusts ≥ `windMph` in the next 12 h | warning |
| Fire nearby | satellite fire detection within 10 mi | warning |
| NWS warnings | any NWS "... Warning" at the site (Tornado / Extreme Wind = stop-work) | warning / stop-work |
| High index | hazard index ≥ `hazardIndexAlert`, unless another alert already covers the top hazard | info |

New alerts are pushed to open browsers (`/alerts/stream`); stop-work alerts are also emailed/texted to every user.

## Background jobs

APScheduler inside the web process (`backend/app/jobs.py`); each job logs and survives failures.

| Job | Every | Source |
|---|---|---|
| Weather | 60 min (`WEATHER_REFRESH_MINUTES`) | Open-Meteo forecast, one request for all sites |
| NWS alerts | 10 min | api.weather.gov, per site |
| River gauges | 30 min | USGS water services, waterway sites (prefers a gauge named after the site's waterway within 40 mi) |
| Fires | 60 min | NASA FIRMS VIIRS 24-hour files (Suomi NPP + NOAA-20) |
| Wildlife | 12 h | iNaturalist, ~1 request per second |
| Lightning | 60 s (`LIGHTNING_POLL_SECONDS`) | NOAA GOES-19 GLM files on AWS (~1 MB/min); `LIGHTNING_SOURCE=off` disables |
| Briefings | 5 min | generates each site's briefing once its local time passes the send time |

## Data sources

| Source | Used for | Notes |
|---|---|---|
| [EIA-860M](https://www.eia.gov/electricity/data/eia860m/) | the 58 job sites (`backend/data/sites.csv`) | rebuild with `scripts/build_sites.py` when a new month is published |
| [Open-Meteo](https://open-meteo.com/) | weather, heat index, rain, gusts, soil moisture, storm energy, 7-day forecast | free tier is non-commercial (10,000 calls/day); set `OPEN_METEO_API_KEY` for commercial use |
| [National Weather Service](https://www.weather.gov/documentation/services-web-api) | official watches, warnings, advisories | set `CONTACT_EMAIL` (sent in the User-Agent, as NWS asks) |
| [USGS Water Services](https://waterservices.usgs.gov/) | river stage and 24-hour change | some large-river stages are published by USACE instead; the nearest USGS gauge is used |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov/) | active fire detections | public 24-hour files, no key |
| [iNaturalist](https://api.inaturalist.org/) | alligator, venomous snake, bear and cougar sightings | public observations |
| [NOAA GOES GLM](https://registry.opendata.aws/noaa-goes/) | lightning flashes | public AWS bucket, read with the pure-Python `pyfive` library |

## Notifications

`backend/app/services/notify.py` sends email over SMTP (`SMTP_*`) and SMS through Twilio (`TWILIO_*`). Without those settings nothing leaves the server: every message is recorded in the `notifications` table with status `logged`, visible in Manage › Briefings.

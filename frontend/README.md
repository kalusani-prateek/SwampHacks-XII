# PlanIT Control frontend

React 19, Tailwind CSS v4, Vite, and React Leaflet for maps.

## Run

```bash
cd frontend
npm install
npm run dev              # http://localhost:5173
npm test                 # unit tests (Node's built-in test runner)
```

The app checks for the backend at startup (`GET /api/meta`):

- **Backend running** (`python run.py` in `backend/`, port 5000, proxied by Vite): live data. On a development server the sign-in page offers the demo accounts `supervisor` and `crew`.
- **No backend:** demo data from `src/mocks/` (58 real plants with generated readings), a **MOCK DATA** badge in the navbar, and any password works. On the dev server the page switches to live data by itself when the backend starts: Vite checks port 5000 every 2 seconds (`backendWatcher` in `vite.config.js`) and tells open pages to reload.

Force one mode with `VITE_USE_MOCKS=true` or `false` in `frontend/.env` (see `.env.example`).

For production, `npm run build` writes `dist/`, which the Flask backend serves on the same port as the API (see `../docs/DEPLOY.md`).

## Roles

There are two roles and no admin. Supervisors hold every management privilege.

- **Crew**: sites, alerts, hazard reporting, briefings and the AI assistant.
- **Supervisor**: everything crew can do, plus the PlanIt Dashboard and the **Manage** panel (`/manage/...`): users and roles, sites, alert rules, hazard-report moderation, briefing settings and the notification outbox.

## Live features

- **Alerts:** new alerts arrive over Server-Sent Events while the tab is visible, with 15-30 s polling as a fallback. A red banner shows stop-work sites on every page, and **🔔 Enable alert notifications** in the navbar turns on browser notifications.
- **Lightning countdown:** each site page counts down the 30-minute all-clear from the latest strike within 10 miles (NOAA GOES satellite data). Supervisors on a development server get **Simulate strike (demo)**.
- **AI assistant:** the floating **Ask PlanIT AI** button opens a chat that knows the site on screen. The browser posts to `POST /api/chat`; the backend calls Claude with live site data ([API § 9](../docs/API.md#9-ai-assistant)). With no backend, a keyword-matching stand-in (`mocks/chatbot.js`, labelled **DEMO**) answers.
- **Offline:** production builds register a service worker (`public/sw.js`) that keeps the app and the last data each page loaded, so crews at remote sites can still open pages without signal. Signing out clears the saved data.

## API calls

All backend calls go through `src/api/`, one file per resource. Search for `REST API PLACEHOLDER` to find each call site; every path is in `src/api/endpoints.js`, and the full contract is in [`../docs/API.md`](../docs/API.md).

## URLs

Every page URL is defined in `src/routes.js`. Never hard-code a path in a component; use the builders:

```js
import { urls } from '../routes.js';
<Link to={urls.site(site.id)} />            // /sites/turkey-point
<Link to={urls.manage('alert-rules')} />    // /manage/alert-rules
navigate(urls.newReport({ site: id }));    // /reports/new?site=turkey-point
```

Filters and searches are kept in the query string (`/alerts?type=lightning`, `/manage/reports?status=open`) through `hooks/useQueryParam.js`, so any view can be bookmarked or shared. Unknown pages and unknown site IDs show a 404 page.

## Structure

```
src/
├── main.jsx        Entry: detects the backend, then renders
├── routes.js       Page URL map (PATHS + urls builders + Manage tab slugs)
├── offline.js      Service worker registration (public/sw.js)
├── api/            REST API service layer, one file per resource
│                   (auth, users, sites, alerts, reports, briefings, settings, stats,
│                    notifications, chat, meta) + endpoints.js + client.js
├── mocks/          Demo data and the demo chatbot (used when no backend answers)
├── context/        AuthContext: signed-in user, login/logout
├── hooks/          useApi, usePolling, useChat, useMeta, useQueryParam, usePageTitle,
│                   useAlertNotifications, useOnlineStatus
├── utils/          url (query strings, slugs, redirect safety), hazard levels, roles, time
├── components/
│   ├── layout/     Navbar, Layout (offline + stop-work banners, chat), ProtectedRoute
│   ├── chat/       ChatWidget (floating assistant), ChatMessage
│   ├── common/     HazardBadge, StatCard, PageHeader, Loading/Error states
│   ├── map/        SiteMap (risk map), LocationPicker (hazard pin)
│   ├── sites/      HazardBreakdown, ConditionsGrid, ForecastChart, SiteRiskTable
│   ├── alerts/     AlertCard, LightningCountdown (30-min all-clear)
│   └── reports/    ReportList
└── pages/
    ├── LoginPage, SitesPage, SiteDetailPage, AlertsPage,
    ├── ReportHazardPage, BriefingsPage, DashboardPage (supervisor), NotFoundPage
    └── manage/     ManagePage (/manage/:tab, supervisor) + tabs/
                    (Overview, Users, Sites, Alert rules, Hazard reports, Briefings)
tests/              url.test.js, hazard.test.js
```

## Brief requirements → where they live

| Requirement | Frontend | Backend |
|---|---|---|
| Combined risk picture per site (50+ real plants) | `pages/SiteDetailPage.jsx`, `components/sites/*` | `services/hazards.py`, `data/sites.csv` (EIA-860M) |
| Instant alerts, lightning stop-work, 30-min countdown | `components/layout/Layout.jsx`, `components/alerts/LightningCountdown.jsx` | `services/lightning.py`, `services/alert_engine.py` |
| Flood warnings for river sites | `pages/AlertsPage.jsx` | `services/rivers.py`, `services/alert_engine.py` |
| 6 PM next-day briefing | `pages/BriefingsPage.jsx`, `manage/tabs/BriefingsTab.jsx` | `services/briefings.py`, `services/notify.py` |
| Crew hazard reporting (photo + map pin) | `pages/ReportHazardPage.jsx`, `components/map/LocationPicker.jsx` | `api/reports.py` |
| Supervisor PlanIt Dashboard | `pages/DashboardPage.jsx` | `api/sites.py` |
| Hazard index (0-10) | `utils/hazard.js`, `components/common/HazardBadge.jsx` | `services/hazards.py` (rule-based; ML model pending) |
| Supervisor management (admin privileges) | `pages/manage/` | `api/users.py`, `api/settings.py` |
| AI assistant | `components/chat/`, `hooks/useChat.js`, `api/chat.js` | `services/assistant.py` |

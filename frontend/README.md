# PlanIT Control frontend

React 19, Tailwind CSS v4, Vite, and React Leaflet for maps.

## Run

```bash
cd frontend
npm install
cp .env.example .env     # optional: mock mode is on by default
npm run dev              # http://localhost:5173
```

In mock mode, sign in as `supervisor` or `crew` with any password.

## Roles

There are two roles and no admin. Supervisors hold every management privilege.

- **Crew**: sites, alerts, hazard reporting, briefings and the AI assistant.
- **Supervisor**: everything crew can do, plus the PlanIt Dashboard and the **Manage** panel (`/manage/...`): users and roles, sites, alert rules, hazard-report moderation and briefing settings.

## AI assistant

A floating **Ask PlanIT AI** button on every signed-in page opens a chat (`components/chat/`). When the user is on a site page, that site is sent as context. The browser never calls the model directly: `src/api/chat.js` posts to `POST /api/chat`, and the Flask backend calls Claude with live site data ([API plan § 9](../docs/API_PLAN.md#9-ai-assistant-apichat)). In mock mode, a keyword-matching stand-in (`mocks/chatbot.js`, labelled **DEMO** in the chat header) answers from the mock data.

## Mock mode vs. the real API

All backend calls go through `src/api/`. Each service function checks `USE_MOCKS`:

- `VITE_USE_MOCKS=true` (default): returns data from `src/mocks/`, using 58 real US power plants as job sites
- `VITE_USE_MOCKS=false`: calls the Flask REST API at `VITE_API_BASE_URL` (default `/api`, proxied to `localhost:5000`)

Search the code for `REST API PLACEHOLDER` to find every place that will hit the backend. The full contract is in [`../docs/API_PLAN.md`](../docs/API_PLAN.md).

## URLs

Every page URL is defined in `src/routes.js` and every API URL in `src/api/endpoints.js`. Never hard-code a path in a component. Use the builders instead:

```js
import { urls } from '../routes.js';
<Link to={urls.site(site.id)} />            // /sites/turkey-point
<Link to={urls.manage('alert-rules')} />    // /manage/alert-rules
navigate(urls.newReport({ site: id }));    // /reports/new?site=turkey-point
```

Filters and searches are kept in the query string (`/alerts?type=lightning`, `/manage/reports?status=open`) through `hooks/useQueryParam.js`, so any view can be bookmarked or shared. Invalid values are dropped from the URL. Unknown pages and unknown site IDs show a 404 page.

## Structure

```
src/
├── routes.js       Page URL map (PATHS + urls builders + Manage tab slugs)
├── api/            REST API service layer, one file per resource
│                   (auth, users, sites, alerts, reports, briefings, settings, stats, chat)
│                   + endpoints.js (every backend path) + client.js (fetch wrapper)
├── mocks/          Mock data and the demo chatbot, used until the backend exists
├── context/        AuthContext: signed-in user, login/logout
├── hooks/          useApi (data loading), usePolling (live refresh), useChat (assistant),
│                   useQueryParam (filters in URL), usePageTitle (tab title)
├── utils/          url (query strings, slugs, redirect safety), hazard levels, roles, time
├── components/
│   ├── layout/     Navbar, Layout (stop-work banner + chat), ProtectedRoute
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
```

## Brief requirements → where they live

| Requirement | Location |
|---|---|
| Combined risk picture per site (50+ real plants) | `pages/SiteDetailPage.jsx`, `components/sites/*`, `mocks/plants.js` |
| Instant alerts, lightning stop-work, 30-min countdown | `components/layout/Layout.jsx`, `components/alerts/LightningCountdown.jsx`, `pages/AlertsPage.jsx` |
| Flood warnings for river sites | `mocks/store.js` (rule), `manage/tabs/AlertRulesTab.jsx` (threshold) |
| 6 PM next-day briefing | `pages/BriefingsPage.jsx`, `manage/tabs/BriefingsTab.jsx` |
| Crew hazard reporting (photo + map pin) | `pages/ReportHazardPage.jsx`, `components/map/LocationPicker.jsx` |
| Supervisor PlanIt Dashboard | `pages/DashboardPage.jsx` |
| Hazard index (0-10) | `utils/hazard.js`, `components/common/HazardBadge.jsx` (the model itself runs in the backend) |
| Supervisor management (admin privileges) | `pages/manage/` |
| AI assistant | `components/chat/`, `hooks/useChat.js`, `api/chat.js` |

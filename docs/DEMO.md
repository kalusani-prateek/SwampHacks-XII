# PlanIT Control demo script (about 5 minutes)

## Before you start

```bash
cd backend && .venv\Scripts\python run.py      # live data; first refresh takes about a minute
cd frontend && npm run dev                     # http://localhost:5173 (or `npm run build` once and use :5000)
```

Optional: set `GEMINI_API_KEY` (free tier) or `ANTHROPIC_API_KEY` in `backend/.env` before starting, so the assistant gives real answers.

## 1. The problem (30 s)

The brief's 6:45 AM scene: heat, storms, mud and a gator, all knowable ahead of time but scattered across a dozen apps. PlanIT Control pulls those sources into one picture per site and turns it into a go/no-go call.

## 2. Supervisor dashboard (60 s)

1. Sign in with the **supervisor** demo button.
2. **PlanIt Dashboard**: 58 real power plants from the federal EIA-860M inventory on a map, ranked by hazard index, with No-go / Caution / Go counts.
3. Point out that the data is live: weather (Open-Meteo), official NWS warnings, USGS river gauges, NASA satellite fire detections, iNaturalist wildlife sightings, and NOAA GOES satellite lightning.

## 3. One site's risk picture (60 s)

1. Open the top-ranked site.
2. Show the **hazard index** and its plain-language reasons, the seven hazard bars, current conditions, the 7-day forecast, and the scoring label: an ML model fitted on three years of NOAA storm reports, plus safety rules it can raise but never lower (method and accuracy in `docs/API.md`). **ML model risk today** in the conditions grid is the model's own estimate.

## 4. Lightning stop-work (60 s)

1. On a site page, press **Simulate strike (demo)**. This stands in for a real GOES strike within 10 miles.
2. **STOP WORK** appears with a **30:00** all-clear countdown; pressing it again restarts the countdown, as the brief requires.
3. The red stop-work banner now shows on every page, and **Alerts** lists it.
4. **Manage › Briefings › Recent notifications** shows the stop-work email recorded in the outbox (real email and SMS once SMTP/Twilio are configured).

## 5. Crew hazard report (45 s)

1. Sign out and sign in as **crew**. The dashboard and Manage disappear, since crew have no management privileges.
2. **Report Hazard**: choose Wildlife, tap the map to pin it, add a photo, then **Send report**.
3. The report appears on the site with its photo, and the site's wildlife score rises.

## 6. Briefings and the assistant (45 s)

1. **Briefings**: tomorrow's briefing for every site. These are sent automatically at 6 PM in each site's own time zone; as supervisor, **Manage › Briefings › Send briefings now** sends them immediately.
2. Open **Ask PlanIT AI** on a site page and ask "Is it safe to work here today?" The AI (Gemini or Claude) answers from that site's live data and never overrides a stop-work. Without an API key, the chat says the key is missing.

## Closing points

- Two roles: supervisors hold all management privileges; there is no separate admin.
- ML scoring learned from three years of NOAA storm reports at these 58 sites and checked on a year it never saw, with the safety rules as a floor.
- Works offline with the last saved data (production build), and sends browser notifications for new alerts.

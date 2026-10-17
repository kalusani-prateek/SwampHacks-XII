# SwampHacks-XII


AI MODEL: 
Pull from 50 real locations Planet conditions ( hazard index )
 - weather
 - extreme heat
 - lightning ( strike within 10 miles causes 30 minute no work)
 - flooding (sites near rivers flood-risk after heavy rain)
 - soil saturation
 - wildlife sightins


Front end: 
Prediction at 6PM releases next day
Crew reports crash/debris
 - photo
 - pin loc on map
 - share to DB for local loc for future project owners
AI chatbot for crews and supervisors to talk to

Supervisor account (has admin privileges; there is no separate admin)
- ranks sites by riskiness
- show where to focus attention/resources

Backend:
 - database to store supervisor/crew
 - pull from weather APIs
 - pull from model
 - database to store incident info
 - Flask RestFUL

## PlanIT Control

Real-time hazard monitoring for utility field crews at 58 real power-plant job sites (from EIA-860M). It combines live weather, NWS warnings, river gauges, satellite fire detections, wildlife sightings and NOAA GOES satellite lightning into one 0-10 hazard index per site. It also raises stop-work alerts (10-mile / 30-minute lightning rule, flood, heat, wind), sends 6 PM next-day briefings, takes crew hazard reports with photos, and answers questions through an AI assistant (Gemini or Claude).

```
backend/     Flask REST API, background data jobs, tests   (backend/README.md)
frontend/    React + Tailwind CSS web app, tests          (frontend/README.md)
docs/        API.md (contract), DEPLOY.md, DEMO.md (5-minute walkthrough)
```

## Quick start

```bash
# Backend (Python 3.12+): http://localhost:5000
cd backend
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py

# Frontend (Node 20.19+): http://localhost:5173, in a second terminal
cd frontend
npm install
npm run dev
```

Sign in with the **supervisor** or **crew** demo button. If the website can't reach the backend, it shows demo data with a **MOCK DATA** badge, then switches to live data by itself once the backend is running, so the start order doesn't matter. Start the backend only once: a second copy exits with a message saying it's already running. Add `GEMINI_API_KEY` (free tier) or `ANTHROPIC_API_KEY` to `backend/.env` to turn on the AI assistant.

On Windows PowerShell, use `npm.cmd` if `npm` is blocked by the script policy.

## Tests

```bash
cd backend && .venv\Scripts\python -m pytest     # 72 API, scoring, alert, assistant and startup tests
cd frontend && npm test                          # URL, hazard-band and demo-assistant tests
```

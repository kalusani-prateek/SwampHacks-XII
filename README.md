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

Real-time hazard monitoring for utility field crews at 58 real power-plant job sites (from EIA-860M). It combines live weather, NWS warnings, river gauges, satellite fire detections, wildlife sightings and NOAA GOES satellite lightning into one 0-10 hazard index per site, scored by an ML model fitted on NOAA storm history plus safety rules. It also raises stop-work alerts (10-mile / 30-minute lightning rule, flood, heat, wind), sends 6 PM next-day briefings, takes crew hazard reports with photos, and answers questions through an AI assistant (Gemini or Claude).

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

On Windows PowerShell, use `npm.cmd` if `npm` is blocked by the script policy. Prefer not to install Python and Node? Use Docker instead (next section).

## Run with Docker

One container runs everything: the API, the background data jobs and the built website, all at **http://localhost:5000**. You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows, macOS) or Docker Engine with Compose v2 (Linux). Python and Node aren't needed.

**1. Settings.** The container reads `backend/.env` if it exists. To start from the template:

```bash
copy backend\.env.example backend\.env      # Windows   (macOS / Linux: cp backend/.env.example backend/.env)
```

`APP_ENV` in that file picks the mode:

| Mode | Set in `backend/.env` | You get |
|---|---|---|
| Demo | `APP_ENV=development` (the template's default) | the **supervisor** / **crew** demo accounts and the *Simulate strike* button |
| Real use | `APP_ENV=production` and `SECRET_KEY=<any long random string>` | no demo accounts; sign-ins survive restarts |

With no `backend/.env`, or no `APP_ENV` in it, the image runs in production mode. Optional extras: `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` for the chatbot, and `CONTACT_EMAIL` (the weather service asks for one). The file stays on your computer: it's passed to the container when it starts and never copied into the image.

**2. Build and start** (from the project folder):

```bash
docker compose up --build
```

The first build takes a few minutes. Open http://localhost:5000 when the log shows `PlanIT Control running on http://0.0.0.0:5000`. Live data fills in over the next minute or two. Add `-d` to run it in the background.

**3. Sign in.**

- **Demo mode:** click **supervisor** or **crew** (password `planit-demo`).
- **Production:** create the first supervisor. The command asks for a username, email and password:

  ```bash
  docker compose exec planit flask --app run create-supervisor
  ```

  Crew members create their own accounts at http://localhost:5000/register.

**Everyday commands**

```bash
docker compose logs -f           # follow the logs
docker compose down              # stop (the database and photos are kept)
docker compose up -d --build     # after pulling new code: rebuild and restart
docker compose down -v           # stop and DELETE the database and photos
```

The database and uploaded photos live in the Docker volumes `planit-data` and `planit-uploads`, so they survive rebuilds and restarts.

<details>
<summary>Without Compose</summary>

```bash
docker build -t planit-control .
docker run -d --name planit -p 5000:5000 --env-file backend/.env -v planit-data:/app/backend/instance -v planit-uploads:/app/backend/uploads planit-control
docker exec -it planit flask --app run create-supervisor
```

Leave out `--env-file backend/.env` if you don't have that file. Stop with `docker stop planit`, and remove with `docker rm planit`.
</details>

**If something goes wrong**

- **"Port 5000 is already allocated":** the local backend (`run.py`) is probably still running, so stop it. Or change `"5000:5000"` to `"8080:5000"` in `compose.yaml` and open http://localhost:8080.
- **Signed out after every restart:** set `SECRET_KEY` in `backend/.env`.
- **Sign-in doesn't stick from another device** (for example a phone at `http://<your-computer's-IP>:5000`): in production mode the session cookie is sent only over HTTPS, and browsers make an exception only for `localhost`. Put the app behind HTTPS (see [docs/DEPLOY.md](docs/DEPLOY.md)), or for local testing set `SESSION_COOKIE_SECURE=false`.
- **Compose complains about `env_file`:** update Docker Desktop (Compose 2.24 or newer reads the optional `backend/.env`), or create `backend/.env`.

## Tests

```bash
cd backend && .venv\Scripts\python -m pytest     # 99 API, scoring, ML, alert, account, assistant and startup tests
cd frontend && npm test                          # URL, hazard-band and demo-assistant tests
```

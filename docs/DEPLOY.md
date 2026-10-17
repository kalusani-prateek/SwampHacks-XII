# Deploying PlanIT Control

One process serves everything: the REST API, the background data jobs and the built React app, on a single port.

## Option A: any server (Windows, macOS or Linux)

1. **Build the frontend**

   ```bash
   cd frontend
   npm ci
   npm run build            # writes frontend/dist, which Flask serves
   ```

2. **Install the backend**

   ```bash
   cd ../backend
   python -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt      # Windows: .venv\Scripts\python
   ```

3. **Configure** (environment variables or `backend/.env`; see `backend/.env.example`)

   | Variable | Required | Notes |
   |---|---|---|
   | `APP_ENV=production` | yes | turns off demo accounts and demo tools, sets secure cookies |
   | `SECRET_KEY` | yes | long random string: `python -c "import secrets; print(secrets.token_hex(32))"` |
   | `CONTACT_EMAIL` | recommended | sent in the User-Agent to the National Weather Service API |
   | `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` | for the assistant | server only; never put it in a `VITE_` variable |
   | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` | for email | without them, emails are only recorded in the outbox |
   | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM` | for SMS | users add phone numbers in E.164 format (`+13055550123`) |
   | `DATABASE_URL` | optional | defaults to SQLite at `backend/instance/planit.db` |

4. **Create the first supervisor**

   ```bash
   .venv/bin/flask --app run create-supervisor
   ```

5. **Start**

   ```bash
   .venv/bin/python serve.py         # PORT (default 5000), HOST, THREADS (default 24)
   ```

6. **Put it behind HTTPS.** Use a reverse proxy such as Caddy or nginx, or your host's TLS. HTTPS is needed for secure cookies, browser notifications and offline support on phones. Serve HTTP/2 through the proxy as well: over plain HTTP/1.1, browsers allow only about six connections per site across all tabs, and each visible tab holds one for the live alert stream.

## Option B: Docker

The repository root has a `Dockerfile` that builds the frontend and runs `serve.py`. It has not been tested yet, because Docker wasn't available on the development machine.

```bash
docker build -t planit-control .
docker run -p 5000:5000 \
  -e SECRET_KEY=change-me -e CONTACT_EMAIL=you@example.com \
  -v planit-data:/app/backend/instance -v planit-uploads:/app/backend/uploads \
  planit-control
docker exec -it <container> flask --app run create-supervisor
```

The two volumes keep the database and uploaded photos when the container is replaced.

## Operating notes

- **Run one instance.** Background jobs, rate limits and live streams live inside the process. Scaling out would need the jobs in a separate worker and a shared store such as Redis.
- **Database:** SQLite (WAL mode) suits a single server. For PostgreSQL, set `DATABASE_URL` and add a driver such as `psycopg[binary]` to `requirements.txt`.
- **Backups:** copy `backend/instance/planit.db` and `backend/uploads/`.
- **Demo accounts:** production never creates them. If the database was first created in development, delete the `supervisor` and `crew` demo users in Manage › Users.
- **Data-source limits and terms:**
  - Open-Meteo's free tier is for non-commercial use (10,000 calls/day; the hourly refresh uses about 2,800). Set `OPEN_METEO_API_KEY` for commercial use.
  - NOAA GOES lightning polling downloads about 1 MB per minute; `LIGHTNING_SOURCE=off` disables it.
  - iNaturalist asks for about one request per second, which the wildlife job respects.
- **Rebuilding the site list:** download the latest EIA-860M workbook and run `python -I scripts/build_sites.py <file.xlsx>`. Sites are seeded only into an empty database, so add new sites to a live database in Manage › Sites.

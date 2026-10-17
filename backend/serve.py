"""Production server (Waitress, works on Windows, macOS and Linux).

    APP_ENV=production SECRET_KEY=... python serve.py

Serves the API, the background jobs and the built frontend (frontend/dist) on
one port. Put it behind HTTPS (a reverse proxy or your host's TLS) in production.
"""
import os

from waitress import serve

from app import create_app
from app.ports import exit_if_port_in_use

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    exit_if_port_in_use(host, port)  # before create_app() starts the background jobs
    app = create_app()
    print(f"PlanIT Control running on http://{host}:{port}")
    # Extra threads: each open browser keeps one Server-Sent Events connection.
    serve(app, host=host, port=port, threads=int(os.environ.get("THREADS", "24")))

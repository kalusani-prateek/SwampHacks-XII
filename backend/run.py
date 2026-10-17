"""Development server: python run.py  ->  http://localhost:5000

Starts the API, the background data jobs and (if frontend/dist exists) the
built web app. For production use serve.py instead.
"""
import os

from app import create_app
from app.ports import exit_if_port_in_use

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    exit_if_port_in_use("127.0.0.1", port)  # before create_app() starts the background jobs
    app = create_app()
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    # The auto-reloader would start the background jobs twice, so it stays off.
    app.run(host="127.0.0.1", port=port, debug=debug, use_reloader=False, threaded=True)
else:
    # Imported by the Flask CLI (flask --app run <command>): a one-off command
    # shouldn't start another copy of the background jobs.
    app = create_app(with_jobs=False)

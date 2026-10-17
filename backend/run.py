"""Development server: python run.py  ->  http://localhost:5000

Starts the API, the background data jobs and (if frontend/dist exists) the
built web app. For production use serve.py instead.
"""
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    # The auto-reloader would start the background jobs twice, so it stays off.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=debug, use_reloader=False, threaded=True)

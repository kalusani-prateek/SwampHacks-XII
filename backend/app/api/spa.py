"""Serves the built React app (frontend/dist) so one server hosts the whole product.

Any non-API path that isn't a real file returns index.html, so client-side
routes like /manage/users survive a page reload.
"""
from flask import Blueprint, current_app, send_from_directory

from ..security import error

bp = Blueprint("spa", __name__)


@bp.get("/", defaults={"path": ""})
@bp.get("/<path:path>")
def frontend(path):
    if path.startswith("api/"):
        return error("Not found", 404)
    dist = current_app.config["FRONTEND_DIST"]
    if not (dist / "index.html").exists():
        return ("Frontend not built yet: run `npm run build` in frontend/, or use the Vite dev server on port 5173.",
                200, {"Content-Type": "text/plain; charset=utf-8"})
    if path and (dist / path).is_file():
        return send_from_directory(dist, path)
    return send_from_directory(dist, "index.html", max_age=0)

"""Next-day briefings: latest per site, one site, and supervisor "send now"."""
from flask import Blueprint, request
from flask_login import login_required

from ..extensions import db
from ..models import Site
from ..security import error, supervisor_required
from ..services import briefings

bp = Blueprint("briefings", __name__)


@bp.get("/briefings")
@login_required
def list_briefings():
    sites = Site.query.filter_by(active=True).all()
    return {"briefings": [b for b in (briefings.latest_for(s) for s in sites) if b]}


@bp.get("/briefings/<site_id>")
@login_required
def get_briefing(site_id):
    site = db.session.get(Site, site_id)
    briefing = briefings.latest_for(site) if site and site.active else None
    return {"briefing": briefing} if briefing else error("Site not found or no forecast yet", 404)


@bp.post("/briefings")
@supervisor_required
def send_briefings():
    site_ids = (request.get_json(silent=True) or {}).get("siteIds")
    if site_ids is not None and not (isinstance(site_ids, list) and all(isinstance(i, str) for i in site_ids)):
        return error("siteIds must be a list of site IDs", 400)
    return {"sent": briefings.send_now(site_ids)}

"""Job sites: list, detail, forecast, lightning status; supervisors add, edit and remove."""
from flask import Blueprint, current_app, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Site
from ..security import error, supervisor_required
from ..services import ingest
from .validation import SLUG, number, slugify, valid_timezone

bp = Blueprint("sites", __name__)

EDITABLE = {"name": "name", "state": "state", "county": "county", "utility": "utility",
            "plantType": "plant_type", "waterway": "waterway", "timezone": "timezone"}


def find_site(site_id, include_inactive=False):
    """The site, or None (paused sites are hidden from everyone but supervisors)."""
    if not SLUG.match(site_id):
        return None
    site = db.session.get(Site, site_id)
    if not site or (not site.active and not (include_inactive or current_user.is_supervisor)):
        return None
    return site


@bp.get("/sites")
@login_required
def list_sites():
    include_inactive = request.args.get("includeInactive") == "true"
    if include_inactive and not current_user.is_supervisor:
        return error("Supervisor privileges required", 403)
    query = Site.query if include_inactive else Site.query.filter_by(active=True)
    return {"sites": [s.to_dict() for s in query.order_by(Site.name)]}


@bp.get("/sites/<site_id>")
@login_required
def get_site(site_id):
    site = find_site(site_id)
    return {"site": site.to_dict()} if site else error("Site not found", 404)


@bp.get("/sites/<site_id>/forecast")
@login_required
def get_forecast(site_id):
    site = find_site(site_id)
    if not site:
        return error("Site not found", 404)
    return {"forecast": [{k: day[k] for k in ("date", "hazardIndex", "topHazard")} for day in site.forecast or []]}


@bp.get("/sites/<site_id>/lightning")
@login_required
def get_lightning(site_id):
    site = find_site(site_id)
    return ingest.lightning_status(site.id) if site else error("Site not found", 404)


@bp.post("/sites/<site_id>/lightning/simulate")
@supervisor_required
def simulate_lightning(site_id):
    """Demo tool (DEMO_TOOLS=true): pretend a strike landed 3 miles away right now."""
    if not current_app.config["DEMO_TOOLS"]:
        return error("Demo tools are turned off on this server", 404)
    site = find_site(site_id)
    if not site:
        return error("Site not found", 404)
    ingest.simulate_strike(site)
    return ingest.lightning_status(site.id)


def apply_fields(site, data, creating):
    """Validate and copy editable fields onto a site. Returns an error message or None."""
    try:
        if "lat" in data or creating:
            site.lat = number(data.get("lat"), -90, 90, "Latitude")
        if "lng" in data or creating:
            site.lng = number(data.get("lng"), -180, 180, "Longitude")
    except ValueError as exc:
        return str(exc)
    for key, attr in EDITABLE.items():
        if key in data:
            value = (data[key] or "").strip() if isinstance(data[key], str) or data[key] is None else data[key]
            setattr(site, attr, value or None)
    if creating and not site.name:
        return "Plant name is required."
    if site.timezone and not valid_timezone(site.timezone):
        return "Unknown time zone."
    if "active" in data:
        site.active = bool(data["active"])
    return None


@bp.post("/sites")
@supervisor_required
def create_site():
    data = request.get_json(silent=True) or {}
    base = slugify(data.get("name") or "") or "site"
    site_id, n = base, 2
    while db.session.get(Site, site_id):
        site_id, n = f"{base}-{n}", n + 1
    site = Site(id=site_id, name="", timezone="America/New_York", active=True)
    problem = apply_fields(site, data, creating=True)
    if problem:
        return error(problem, 400)
    db.session.add(site)
    db.session.commit()
    ingest.rescore([site])
    return {"site": site.to_dict()}, 201


@bp.put("/sites/<site_id>")
@supervisor_required
def update_site(site_id):
    site = find_site(site_id, include_inactive=True)
    if not site:
        return error("Site not found", 404)
    problem = apply_fields(site, request.get_json(silent=True) or {}, creating=False)
    if problem:
        db.session.rollback()
        return error(problem, 400)
    db.session.commit()
    ingest.rescore([site])
    return {"message": "Site updated", "site": site.to_dict()}


@bp.delete("/sites/<site_id>")
@supervisor_required
def delete_site(site_id):
    site = find_site(site_id, include_inactive=True)
    if not site:
        return error("Site not found", 404)
    db.session.delete(site)
    db.session.commit()
    return {"message": "Site deleted"}

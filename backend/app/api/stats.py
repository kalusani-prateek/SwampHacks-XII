"""Headline numbers for Manage > Overview."""
from flask import Blueprint

from ..models import Alert, HazardReport, Site, User
from ..security import supervisor_required

bp = Blueprint("stats", __name__)


@bp.get("/stats")
@supervisor_required
def stats():
    sites = Site.query.filter_by(active=True)
    return {"stats": {
        "sites": sites.count(),
        "noGoSites": sites.filter(Site.hazard_index > 7.5).count(),
        "activeAlerts": Alert.query.filter_by(active=True).count(),
        "openReports": HazardReport.query.filter_by(status="open").count(),
        "users": User.query.count(),
    }}

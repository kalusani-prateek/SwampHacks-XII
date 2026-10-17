"""Supervisor settings: alert thresholds and the briefing schedule."""
import re

from flask import Blueprint, request
from flask_login import login_required

from ..models import ROLES
from ..security import error, supervisor_required
from ..settings_store import get_setting, set_setting
from .validation import number

bp = Blueprint("settings", __name__)

# Field -> (minimum, maximum) for alert rules.
RULE_LIMITS = {
    "lightningRadiusMiles": (1, 50),
    "lightningAllClearMinutes": (5, 120),
    "floodRainInches": (0.1, 20),
    "heatIndexF": (80, 140),
    "windMph": (10, 100),
    "hazardIndexAlert": (1, 10),
}


@bp.get("/settings/alert-rules")
@login_required
def get_rules():
    return {"rules": get_setting("alert_rules")}


@bp.put("/settings/alert-rules")
@supervisor_required
def put_rules():
    incoming = (request.get_json(silent=True) or {}).get("rules") or {}
    rules = get_setting("alert_rules")
    try:
        for field, (low, high) in RULE_LIMITS.items():
            if field in incoming:
                rules[field] = number(incoming[field], low, high, field)
    except ValueError as exc:
        return error(str(exc), 400)
    return {"rules": set_setting("alert_rules", rules)}


@bp.get("/settings/briefings")
@supervisor_required
def get_briefing_settings():
    return {"settings": get_setting("briefing_settings")}


@bp.put("/settings/briefings")
@supervisor_required
def put_briefing_settings():
    incoming = (request.get_json(silent=True) or {}).get("settings") or {}
    settings = get_setting("briefing_settings")
    if "enabled" in incoming:
        settings["enabled"] = bool(incoming["enabled"])
    if "localTime" in incoming:
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(incoming["localTime"])):
            return error("Send time must be HH:MM (24-hour)", 400)
        settings["localTime"] = incoming["localTime"]
    if "channels" in incoming:
        channels = incoming["channels"] or {}
        settings["channels"] = {name: bool(channels.get(name, False)) for name in ("email", "sms", "push")}
    if "recipients" in incoming:
        recipients = incoming["recipients"]
        if not isinstance(recipients, list) or any(r not in ROLES for r in recipients):
            return error(f"Recipients must be roles: {', '.join(ROLES)}", 400)
        settings["recipients"] = recipients
    return {"settings": set_setting("briefing_settings", settings)}

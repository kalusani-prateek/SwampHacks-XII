"""Next-day safety briefings.

Built from each site's forecast and generated when the site's local time
passes the send time (6 PM by default). All briefings due in one run go out
as a single digest per recipient, on the channels enabled in the settings.
"""
from datetime import date, time, timedelta, timezone
from zoneinfo import ZoneInfo

from ..extensions import db
from ..models import Briefing, Site, utcnow
from ..settings_store import get_setting
from . import notify
from .events import bus
from .hazards import CONTROLS, LABELS, level


def local_now(site, now=None):
    return (now or utcnow()).replace(tzinfo=timezone.utc).astimezone(ZoneInfo(site.timezone))


def build_briefing(site):
    """Tomorrow's briefing from the site's stored forecast, or None before the first weather refresh."""
    forecast = site.forecast or []
    if not forecast:
        return None
    day = forecast[0]
    top = sorted(day["hazards"].items(), key=lambda kv: kv[1], reverse=True)[:3]
    band = level(day["hazardIndex"])
    return {
        "siteId": site.id,
        "siteName": site.name,
        "state": site.state,
        "timezone": site.timezone,
        "forDate": day["date"],
        "hazardIndex": day["hazardIndex"],
        "decision": band["decision"],
        "summary": f"{band['label']} risk expected tomorrow at {site.name}. Primary concern: {LABELS[top[0][0]].lower()}.",
        "topHazards": [{"key": key, "score": score, "control": CONTROLS[key]} for key, score in top],
    }


def latest_for(site):
    """The stored briefing for the site's tomorrow, or a live preview if it hasn't been generated yet."""
    tomorrow = local_now(site).date() + timedelta(days=1)
    stored = Briefing.query.filter_by(site_id=site.id, for_date=tomorrow).first()
    if stored:
        return {**stored.payload, "generated": True}
    preview = build_briefing(site)
    return {**preview, "generated": False} if preview else None


def generate(sites):
    """Create (or replace) tomorrow's briefing for each site. Returns the payloads."""
    payloads = []
    for site in sites:
        payload = build_briefing(site)
        if not payload:
            continue
        for_date = date.fromisoformat(payload["forDate"])
        row = Briefing.query.filter_by(site_id=site.id, for_date=for_date).first()
        if row:
            row.payload, row.generated_at = payload, utcnow()
        else:
            db.session.add(Briefing(site_id=site.id, for_date=for_date, payload=payload))
        payloads.append(payload)
    db.session.commit()
    return payloads


def deliver(payloads, settings):
    """One digest per recipient, riskiest sites first; plus a live push to open browsers."""
    ranked = sorted(payloads, key=lambda p: p["hazardIndex"], reverse=True)
    lines = []
    for p in ranked:
        lines.append(f"{p['siteName']} ({p['state']}), {p['forDate']}: {p['hazardIndex']:.1f}/10, {p['decision']}")
        lines.append(f"  {p['summary']}")
        lines.extend(f"  - {LABELS[h['key']]}: {h['control']}" for h in p["topHazards"][:2])
    subject = f"PlanIT next-day safety briefing ({len(ranked)} site{'s' if len(ranked) != 1 else ''})"
    sms = "PlanIT briefing: " + "; ".join(f"{p['siteName']} {p['decision']}" for p in ranked[:4])
    channels = [name for name in ("email", "sms") if settings["channels"].get(name)]
    if channels:
        notify.notify_roles(settings["recipients"], subject, "\n".join(lines), sms, channels)
    if settings["channels"].get("push"):
        bus.publish({"type": "briefing", "count": len(ranked)})
    now = utcnow()
    for row in Briefing.query.filter(Briefing.site_id.in_([p["siteId"] for p in ranked]), Briefing.sent_at.is_(None)):
        row.sent_at = now
    db.session.commit()


def run_due():
    """Every few minutes: briefings for sites whose local time just passed the send time."""
    settings = get_setting("briefing_settings")
    if not settings["enabled"]:
        return 0
    send_at = time.fromisoformat(settings["localTime"])
    due = []
    for site in Site.query.filter_by(active=True):
        local = local_now(site)
        if local.time() < send_at:
            continue
        if not Briefing.query.filter_by(site_id=site.id, for_date=local.date() + timedelta(days=1)).first():
            due.append(site)
    payloads = generate(due)
    if payloads:
        deliver(payloads, settings)
    return len(payloads)


def send_now(site_ids=None):
    """Manual trigger (Manage > Briefings): generate and send tomorrow's briefings now."""
    query = Site.query.filter_by(active=True)
    if site_ids:
        query = query.filter(Site.id.in_(site_ids))
    payloads = generate(query.all())
    if payloads:
        deliver(payloads, get_setting("briefing_settings"))
    return len(payloads)

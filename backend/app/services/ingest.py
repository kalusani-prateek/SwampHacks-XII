"""Refresh jobs: fetch each data source, save the readings, rescore sites and update alerts.

Fetching happens outside the write lock; saving and scoring happen inside it,
so only one thread writes to the database at a time (SQLite-friendly).
"""
import logging
import threading
import time
from datetime import timedelta

from flask import current_app

from ..extensions import db
from ..models import Alert, HazardReport, LightningStrike, Site, iso, utcnow
from ..settings_store import get_setting
from . import alert_engine, fires, lightning, notify, nws, push, rivers, weather, wildlife
from .events import bus
from .hazards import level, lightning_summary, score_site

log = logging.getLogger(__name__)
WRITE_LOCK = threading.RLock()
_poller = lightning.GlmPoller()


def active_sites():
    return Site.query.filter_by(active=True).order_by(Site.id).all()


def recent_strikes(site_id, now):
    rows = LightningStrike.query.filter(
        LightningStrike.site_id == site_id, LightningStrike.observed_at >= now - timedelta(hours=2)
    ).all()
    return [{"observedAt": row.observed_at, "distance": row.distance_miles} for row in rows]


def lightning_status(site_id, rules=None):
    """Latest strike within the stop-work radius (drives the 30-minute countdown in the UI)."""
    rules = rules or get_setting("alert_rules")
    now = utcnow()
    summary = lightning_summary(recent_strikes(site_id, now), rules, now)
    return {
        "lastStrikeAt": iso(summary["lastStrikeAt"]),
        "distanceMiles": summary["distanceMiles"],
        "strikesLastHour": summary["strikes1h"],
    }


def crew_wildlife_reports(site_id, now):
    return HazardReport.query.filter(
        HazardReport.site_id == site_id,
        HazardReport.type == "wildlife",
        HazardReport.status != "dismissed",
        HazardReport.created_at >= now - timedelta(days=7),
    ).count()


def rescore(sites):
    """Recompute scores and alerts for these sites; announce any new alerts.

    All reads happen first and all writes at the end, so the database write
    transaction stays short and doesn't block requests (e.g. sending briefings)."""
    if not sites:
        return []
    rules = get_setting("alert_rules")
    now = utcnow()
    created = []
    with WRITE_LOCK:
        with db.session.no_autoflush:
            active = alert_engine.active_by_site([s.id for s in sites])
            results = []
            for site in sites:
                readings = {"waterway": site.waterway, "lat": site.lat, "lng": site.lng, "weather": site.weather,
                            "nws": site.nws, "river": site.river, "fire": site.fire, "wildlife": site.wildlife}
                scored = score_site(readings, recent_strikes(site.id, now), crew_wildlife_reports(site.id, now), rules, now)
                results.append((site, scored))
        turned_no_go = []
        for site, scored in results:
            if level(site.hazard_index or 0)["decision"] != "NO-GO" and level(scored["hazardIndex"])["decision"] == "NO-GO":
                turned_no_go.append(site)
            site.hazard_index = scored["hazardIndex"]
            site.hazards = scored["hazards"]
            site.conditions = scored["conditions"]
            site.drivers = scored["drivers"]
            site.forecast = scored["forecast"]
            site.scored_at = now
            wanted = alert_engine.wanted_alerts(site, scored, rules)
            created += alert_engine.sync_alerts(site, wanted, now, active[site.id])
        db.session.commit()
    announce(created)
    for site in turned_no_go:  # phone/desktop notification for the people who work there
        push.notify_no_go(site)
    return created


def announce(alerts):
    """Push new alerts to open browsers; stop-work alerts also go out by email/SMS."""
    for alert in alerts:
        bus.publish({"type": "alert", "alertId": alert.id, "siteId": alert.site_id,
                     "severity": alert.severity, "title": alert.title})
    stop_work = [a for a in alerts if a.severity == "stop-work"]
    if stop_work:
        names = ", ".join(a.site.name for a in stop_work)
        body = "\n".join(f"{a.site.name}: {a.title}. {a.message}" for a in stop_work)
        notify.notify_roles(["crew", "supervisor"], f"PlanIT STOP WORK: {names}", body, sms_body=body[:300])


def store(field, results):
    """Save one source's readings ({site_id: data}) onto the sites, then rescore them."""
    with WRITE_LOCK:
        sites = [s for s in (db.session.get(Site, site_id) for site_id in results) if s]
        for site in sites:
            setattr(site, field, results[site.id])
        db.session.commit()
    rescore(sites)
    return len(sites)


def refresh_weather():
    sites = active_sites()
    return store("weather", weather.fetch_all(sites, current_app.config["OPEN_METEO_API_KEY"]))


def refresh_nws():
    results = {}
    for site in active_sites():
        try:
            results[site.id] = nws.fetch_alerts(site)
        except Exception as exc:
            log.warning("NWS alerts failed for %s: %s", site.id, exc)
        time.sleep(0.2)
    return store("nws", results)


def refresh_rivers():
    results = {}
    for site in active_sites():
        if not site.waterway:
            continue
        try:
            results[site.id] = rivers.fetch_river(site, site.river)
        except Exception as exc:
            log.warning("USGS gauge failed for %s: %s", site.id, exc)
        time.sleep(0.2)
    return store("river", results)


def refresh_fires():
    sites = active_sites()
    return store("fire", fires.nearest_by_site(sites, fires.fetch_detections()))


def refresh_wildlife():
    ids = wildlife.taxon_ids()
    results = {}
    for site in active_sites():
        try:
            results[site.id] = wildlife.fetch_sightings(site, ids)
        except Exception as exc:
            log.warning("iNaturalist failed for %s: %s", site.id, exc)
        time.sleep(1.0)  # iNaturalist asks for ~1 request per second
    return store("wildlife", results)


def refresh_lightning():
    """Poll GOES lightning files, store nearby flashes, rescore affected sites."""
    sites = active_sites()
    matches = _poller.poll(sites, current_app.config["GLM_SATELLITES"])
    now = utcnow()
    with WRITE_LOCK:
        for site_id, observed_at, miles in matches:
            db.session.add(LightningStrike(site_id=site_id, observed_at=observed_at, distance_miles=miles, source="glm"))
        LightningStrike.query.filter(LightningStrike.observed_at < now - timedelta(hours=3)).delete()
        db.session.commit()
    rescore_lightning_sites({site_id for site_id, _, _ in matches})
    return len(matches)


def rescore_lightning_sites(extra_ids=()):
    """Rescore sites with new strikes or an active lightning alert (so alerts clear after the all-clear)."""
    ids = set(extra_ids) | {a.site_id for a in Alert.query.filter_by(active=True, key="lightning")}
    if ids:
        rescore(Site.query.filter(Site.id.in_(ids)).all())


def simulate_strike(site, miles=3.0):
    """Demo tool: record a strike near a site right now."""
    with WRITE_LOCK:
        db.session.add(LightningStrike(site_id=site.id, observed_at=utcnow(), distance_miles=miles, source="simulated"))
        db.session.commit()
    rescore([site])


def refresh_all():
    """Run every source once (CLI: flask --app run refresh)."""
    for job in (refresh_weather, refresh_nws, refresh_rivers, refresh_fires, refresh_wildlife):
        try:
            log.info("%s: %s sites updated", job.__name__, job())
        except Exception:
            log.exception("%s failed", job.__name__)

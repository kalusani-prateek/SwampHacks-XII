"""Alert rules: turns a site's scores into alerts.

One active alert per (site, rule key). Each refresh creates alerts for newly
broken rules, updates the text of continuing ones, and clears the rest. The
lightning alert clears on its own once the all-clear window passes with no new
strike within the radius.
"""
from ..extensions import db
from ..models import Alert, utcnow
from .hazards import NWS_RULES

STOP_WORK_NWS = {"Tornado Warning", "Extreme Wind Warning"}


def wanted_alerts(site, scored, rules):
    """{key: (type, severity, title, message)} for every rule this site currently breaks."""
    wanted = {}
    readings, bolt = scored["readings"], scored["lightning"]
    radius, minutes = rules["lightningRadiusMiles"], rules["lightningAllClearMinutes"]

    if bolt["stopWork"]:
        wanted["lightning"] = (
            "lightning", "stop-work", f"STOP WORK: lightning within {radius:g} miles",
            f"Strike {bolt['distanceMiles']:.0f} mi away. All-clear {minutes:g} minutes after the last strike; "
            "the countdown restarts with each new strike.",
        )

    rain, rise = readings["precip24hIn"] or 0, readings["riverChange24hFt"] or 0
    if site.waterway and (rain >= rules["floodRainInches"] or rise >= 2):
        detail = f'{rain:.1f}" of rain in 24 h' + (f", river up {rise:.1f} ft" if rise >= 1 else "")
        wanted["flood"] = (
            "flooding", "warning", "Flood-risk warning",
            f"{detail} on the {site.waterway}. Keep off low ground and check the gauge before moving equipment.",
        )

    heat = readings["heatIndexF"]
    if heat is not None and heat >= rules["heatIndexF"]:
        wanted["heat"] = ("heat", "warning", "Extreme heat advisory",
                          f"Heat index up to {heat:.0f}°F in the next 12 h. Enforce water-rest-shade.")

    gust = readings["gustMph"]
    if gust is not None and gust >= rules["windMph"]:
        wanted["wind"] = ("wind", "warning", "High wind: check crane and lift limits",
                          f"Gusts to {gust:.0f} mph in the next 12 h.")

    fire = readings["nearestFireMiles"]
    if fire is not None and fire <= 10:
        wanted["wildfire"] = ("wildfire", "warning", "Active fire nearby",
                              f"Satellite fire detection {fire:.0f} mi away. No hot work; plan two evacuation routes.")

    for nws_alert in readings["nwsAlerts"]:
        event = nws_alert.get("event") or ""
        if event.endswith("Warning"):
            category = NWS_RULES.get(event, ("wind", 0))[0]
            severity = "stop-work" if event in STOP_WORK_NWS else "warning"
            wanted[f"nws:{event}"] = (category, severity, f"NWS {event}", nws_alert.get("headline") or event)

    # High overall index, unless a specific alert already covers the top hazard (no duplicate alerts).
    top = max(scored["hazards"], key=scored["hazards"].get)
    if scored["hazardIndex"] >= rules["hazardIndexAlert"] and all(kind != top for kind, *_ in wanted.values()):
        wanted["index"] = (top, "info", "High hazard index",
                           f"Hazard index {scored['hazardIndex']:.1f}/10. Review conditions before work starts.")
    return wanted


def active_by_site(site_ids):
    """{site_id: {key: Alert}} for the currently active alerts of these sites (one query)."""
    grouped = {site_id: {} for site_id in site_ids}
    for alert in Alert.query.filter(Alert.site_id.in_(list(site_ids)), Alert.active.is_(True)):
        grouped[alert.site_id][alert.key] = alert
    return grouped


def sync_alerts(site, wanted, now=None, active=None):
    """Create, refresh and clear this site's alerts. Returns the newly created ones.

    `active` is the site's current {key: Alert} map (looked up if not given)."""
    now = now or utcnow()
    active = dict(active) if active is not None else active_by_site([site.id])[site.id]
    created = []
    for key, (kind, severity, title, message) in wanted.items():
        alert = active.pop(key, None)
        if alert is None:
            alert = Alert(site_id=site.id, key=key, type=kind, severity=severity, title=title, message=message,
                          created_at=now, updated_at=now)
            db.session.add(alert)
            created.append(alert)
        elif (alert.title, alert.message, alert.severity) != (title, message, severity):
            alert.title, alert.message, alert.severity, alert.updated_at = title, message, severity, now
    for alert in active.values():  # the condition has cleared
        alert.active = False
        alert.cleared_at = now
    return created

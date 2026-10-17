"""Hazard scoring for job sites.

Turns a site's latest readings (weather, NWS alerts, lightning, river gauge,
fires, wildlife) into seven 0-10 hazard scores, one hazard index, short
plain-language "drivers" and a 7-day forecast.

Method: transparent rule-based scoring. Each hazard maps a measured value onto
0-10 with the breakpoints below (NWS heat-index categories, the brief's
10-mile / 30-minute lightning rule, common crane wind limits). Official NWS
warnings set a minimum score. A trained ML model can later replace combine();
SCORING tells the UI which method produced the numbers.
"""
from datetime import timedelta

HAZARD_KEYS = ["heat", "lightning", "flooding", "wildfire", "soil", "wildlife", "wind"]
SCORING = {"method": "rule-based", "label": "Rule-based scoring of live conditions (ML model pending)"}

LABELS = {
    "heat": "Extreme heat",
    "lightning": "Lightning",
    "flooding": "Flooding",
    "wildfire": "Wildfire",
    "soil": "Soil saturation",
    "wildlife": "Wildlife",
    "wind": "Wind / storms",
}

# (measured value, score) breakpoints; values in between are interpolated.
HEAT_INDEX_F = [(80, 0), (90, 3), (103, 6), (115, 9), (125, 10)]   # NWS: caution 80, extreme caution 90, danger 103
GUST_MPH = [(15, 0), (25, 3), (35, 6), (45, 8), (55, 10)]           # many cranes and lifts stop near 30-35 mph
RAIN_24H_IN = [(0, 0), (0.5, 2), (1, 3.5), (2, 6), (4, 9), (6, 10)]
RIVER_RISE_FT = [(0, 0), (1, 2), (3, 6), (6, 9), (10, 10)]           # stream gauge change over 24 h
SOIL_M3M3 = [(0.15, 0), (0.25, 3), (0.35, 6), (0.42, 8), (0.48, 10)]  # volumetric water content, 3-9 cm deep
CAPE_JKG = [(0, 0), (1000, 2), (2500, 4), (4000, 5.5)]              # storm energy; actual lightning scores higher
WILDLIFE_SIGHTINGS = [(0, 0), (1, 3), (3, 5), (10, 6.5)]             # dangerous-species sightings within 10 mi, 30 days
THUNDER_CODES = {95, 96, 99}                                         # WMO weather codes for thunderstorms
NEARBY_LIGHTNING_MILES = 30

# Official NWS alerts: (hazard category, minimum score). The index never drops below the floor.
NWS_RULES = {
    "Tornado Warning": ("wind", 10), "Extreme Wind Warning": ("wind", 10), "Hurricane Warning": ("wind", 10),
    "Tropical Storm Warning": ("wind", 8), "High Wind Warning": ("wind", 7.5), "Tornado Watch": ("wind", 6),
    "Hurricane Watch": ("wind", 6), "Wind Advisory": ("wind", 5),
    "Severe Thunderstorm Warning": ("lightning", 8), "Severe Thunderstorm Watch": ("lightning", 5.5),
    "Flash Flood Warning": ("flooding", 8.5), "Flood Warning": ("flooding", 7), "Coastal Flood Warning": ("flooding", 7),
    "Storm Surge Warning": ("flooding", 8.5), "Flash Flood Watch": ("flooding", 5), "Flood Watch": ("flooding", 5),
    "Flood Advisory": ("flooding", 4),
    "Extreme Heat Warning": ("heat", 8), "Excessive Heat Warning": ("heat", 8), "Heat Advisory": ("heat", 6),
    "Extreme Heat Watch": ("heat", 5), "Excessive Heat Watch": ("heat", 5),
    "Red Flag Warning": ("wildfire", 7), "Fire Weather Watch": ("wildfire", 4.5),
}

# Recommended controls per hazard, used in briefings and drivers.
CONTROLS = {
    "heat": "Water-rest-shade: about 1 cup of water every 15-20 minutes, shaded breaks, start heavy work early.",
    "lightning": "Stop work for any strike within 10 mi; resume only after a 30-minute all-clear.",
    "flooding": "Keep off low ground and levee toes; check the river gauge before moving equipment.",
    "wildfire": "No hot work; stage extinguishers; plan two evacuation routes.",
    "soil": "Use mats or the temporary road; keep heavy equipment off saturated ground.",
    "wildlife": "Spotter on water edges; keep 30 ft from alligators and snakes; report sightings in the app.",
    "wind": "Ground cranes and aerial lifts above the manufacturer's wind limits.",
}

LEVELS = [
    (2.5, "Low", "GO"),
    (5.0, "Moderate", "GO"),
    (7.5, "High", "CAUTION"),
    (10.0, "Extreme", "NO-GO"),
]


def ramp(value, points):
    """Piecewise-linear map of a reading onto a 0-10 score (clamped at both ends)."""
    if value is None:
        return 0.0
    if value <= points[0][0]:
        return float(points[0][1])
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if value <= x2:
            return y1 + (y2 - y1) * (value - x1) / (x2 - x1)
    return float(points[-1][1])


def combine(scores):
    """One 0-10 index, weighted toward the worst hazard: one extreme hazard dominates."""
    ranked = sorted(scores.values(), reverse=True)
    mean = sum(ranked) / len(ranked)
    return round(min(10.0, 0.6 * ranked[0] + 0.25 * ranked[1] + 0.15 * mean), 1)


def level(index):
    """Band for a 0-10 index: label plus the go / caution / no-go call."""
    for upper, label, decision in LEVELS:
        if index <= upper:
            return {"label": label, "decision": decision}
    return {"label": "Extreme", "decision": "NO-GO"}


def _max(*values):
    present = [v for v in values if v is not None]
    return max(present) if present else None


def _round(value, digits=1):
    return None if value is None else round(value, digits)


def lightning_summary(strikes, rules, now):
    """Stop-work state from strikes (dicts with observedAt and distance, newest last or any order)."""
    radius = rules["lightningRadiusMiles"]
    window = timedelta(minutes=rules["lightningAllClearMinutes"])
    hour_ago = now - timedelta(hours=1)
    within = [s for s in strikes if s["distance"] <= radius]
    latest = max(within, key=lambda s: s["observedAt"]) if within else None
    return {
        "stopWork": bool(latest and now - latest["observedAt"] <= window),
        "lastStrikeAt": latest["observedAt"] if latest else None,
        "distanceMiles": latest["distance"] if latest else None,
        "strikes1h": sum(1 for s in within if s["observedAt"] >= hour_ago),
        "nearby1h": sum(1 for s in strikes if s["observedAt"] >= hour_ago),
    }


def score_site(site, strikes, crew_wildlife_reports, rules, now):
    """Score one site.

    site: dict with "waterway" and the raw JSON readings "weather", "nws", "river", "fire", "wildlife"
    strikes: lightning strikes within 30 mi in the last 2 h, as dicts {"observedAt": datetime, "distance": miles}
    crew_wildlife_reports: crew wildlife reports at this site in the last 7 days
    rules: alert rules (lightning radius / all-clear minutes)
    now: current time, naive UTC
    """
    weather = site.get("weather") or {}
    current = weather.get("current") or {}
    river = site.get("river") or {}
    fire = site.get("fire") or {}
    wildlife = site.get("wildlife") or {}
    nws_alerts = (site.get("nws") or {}).get("alerts") or []
    waterway = site.get("waterway")

    hazards = {}
    drivers = []  # (priority, text); higher priority shown first

    # Lightning: real strikes beat storm forecasts.
    bolt = lightning_summary(strikes, rules, now)
    cape = weather.get("capeNext12h")
    today = _today(weather)
    if bolt["stopWork"]:
        minutes = int((now - bolt["lastStrikeAt"]).total_seconds() // 60)
        hazards["lightning"] = 10.0
        drivers.append((100, f"Lightning {bolt['distanceMiles']:.0f} mi away {minutes} min ago: stop work"))
    elif bolt["nearby1h"]:
        hazards["lightning"] = 7.0
        drivers.append((60, f"{bolt['nearby1h']} lightning flashes within {NEARBY_LIGHTNING_MILES} mi in the last hour"))
    else:
        storm_today = (current.get("weatherCode") in THUNDER_CODES) or (today.get("weatherCode") in THUNDER_CODES)
        hazards["lightning"] = max(ramp(cape, CAPE_JKG), 5.0 if storm_today else 0.0)
        if storm_today:
            drivers.append((30, "Thunderstorms in today's forecast"))

    # Heat: the worst heat index over the next 12 hours.
    heat_index = _max(current.get("heatIndexF"), weather.get("heatIndexNext12hF"))
    hazards["heat"] = ramp(heat_index, HEAT_INDEX_F)
    if hazards["heat"] >= 3:
        drivers.append((hazards["heat"] * 5, f"Heat index up to {heat_index:.0f}°F in the next 12 h"))

    # Wind: the strongest gust over the next 12 hours.
    gust = _max(current.get("gustMph"), weather.get("gustNext12hMph"))
    hazards["wind"] = ramp(gust, GUST_MPH)
    if hazards["wind"] >= 3:
        drivers.append((hazards["wind"] * 5, f"Gusts to {gust:.0f} mph: check crane and aerial lift limits"))

    # Flooding: recent rain, plus the river gauge for sites on a waterway.
    rain = weather.get("precip24hIn")
    flood = ramp(rain, RAIN_24H_IN)
    if not waterway:
        flood = min(flood, 8.0)
    rise = river.get("change24hFt")
    if waterway and rise is not None and rise > 0:
        flood = max(flood, ramp(rise, RIVER_RISE_FT))
        if rise >= 1:
            drivers.append((flood * 5, f"{river.get('gaugeName') or waterway} up {rise:.1f} ft in 24 h"))
    hazards["flooding"] = flood
    if rain and ramp(rain, RAIN_24H_IN) >= 3:
        drivers.append((flood * 5, f'{rain:.1f}" of rain in the last 24 h' + (f" on the {waterway}" if waterway else "")))

    # Wildfire: satellite fire detections nearby, worse when it is dry and windy.
    nearest_fire = fire.get("nearestMiles")
    fire_score = 0.0
    if nearest_fire is not None:
        fire_score = 9.0 if nearest_fire <= 5 else 7.0 if nearest_fire <= 10 else 4.0 if nearest_fire <= 25 else 0.0
    dry_windy = (today.get("humidityMinPct") or 100) < 20 and (gust or 0) >= 25
    if dry_windy:
        fire_score = min(10.0, max(fire_score + 2, 3.0))
    hazards["wildfire"] = fire_score
    if nearest_fire is not None and nearest_fire <= 25:
        drivers.append((fire_score * 5, f"Active fire detected {nearest_fire:.0f} mi away (NASA satellite)"))
    elif dry_windy:
        drivers.append((15, "Dry and windy: elevated fire danger"))

    # Soil saturation: soft ground strands vehicles and equipment.
    soil = weather.get("soilMoisture")
    hazards["soil"] = ramp(soil, SOIL_M3M3)
    if hazards["soil"] >= 5:
        drivers.append((hazards["soil"] * 4, f"Soil moisture {soil * 100:.0f}%: soft ground, vehicles may get stuck"))

    # Wildlife: crew reports at this site, plus iNaturalist sightings nearby.
    sightings = wildlife.get("count30d") or 0
    hazards["wildlife"] = max(ramp(sightings, WILDLIFE_SIGHTINGS), 7.0 if crew_wildlife_reports else 0.0)
    if crew_wildlife_reports:
        drivers.append((35, f"{crew_wildlife_reports} crew wildlife report(s) at this site this week"))
    elif sightings:
        names = sorted({r["name"] for r in wildlife.get("recent", []) if r.get("name")})[:2]
        detail = f" ({', '.join(names)})" if names else ""
        drivers.append((12, f"{sightings} dangerous-wildlife sightings within 10 mi in 30 days{detail}"))

    # Official NWS alerts set minimum scores.
    index_floor = 8.0 if bolt["stopWork"] else 0.0
    for alert in nws_alerts:
        rule = NWS_RULES.get(alert.get("event"))
        if not rule:
            continue
        category, floor = rule
        hazards[category] = max(hazards[category], float(floor))
        index_floor = max(index_floor, float(floor))
        drivers.append((50 + floor, f"NWS {alert['event']}"))

    hazards = {key: round(hazards[key], 1) for key in HAZARD_KEYS}
    hazard_index = round(max(combine(hazards), index_floor), 1)

    shown, seen = [], set()
    for _priority, text in sorted(drivers, key=lambda d: d[0], reverse=True):
        if text not in seen:
            seen.add(text)
            shown.append(text)
    drivers_out = shown[:4] or ["No significant hazards right now"]

    conditions = {
        "tempF": _round(current.get("tempF"), 0),
        "heatIndexF": _round(current.get("heatIndexF"), 0),
        "humidityPct": _round(current.get("humidityPct"), 0),
        "windMph": _round(current.get("windMph"), 0),
        "windGustMph": _round(current.get("gustMph"), 0),
        "precip24hIn": _round(rain, 2),
        "soilMoisturePct": None if soil is None else round(soil * 100),
        "lightningStrikes1h": bolt["strikes1h"],
        "riverStageFt": _round(river.get("stageFt"), 1),
        "riverChange24hFt": _round(rise, 1),
        "nearestFireMiles": _round(nearest_fire, 0) if nearest_fire is not None and nearest_fire <= 100 else None,
        "wildlifeSightings30d": sightings,
        "nwsAlerts": len(nws_alerts),
    }
    conditions = {key: value for key, value in conditions.items() if value is not None}

    return {
        "hazards": hazards,
        "hazardIndex": hazard_index,
        "drivers": drivers_out,
        "conditions": conditions,
        "forecast": forecast_days(weather, hazards, waterway),
        "lightning": bolt,
        "readings": {
            "heatIndexF": heat_index,
            "gustMph": gust,
            "precip24hIn": rain,
            "riverChange24hFt": rise,
            "nearestFireMiles": nearest_fire,
            "nwsAlerts": nws_alerts,
        },
    }


def _today(weather):
    daily = weather.get("daily") or []
    index = weather.get("todayIndex", 0)
    return daily[index] if 0 <= index < len(daily) else {}


def forecast_days(weather, hazards_now, waterway, days=7):
    """Score each of the next `days` days from the daily forecast (dates are site-local)."""
    daily = weather.get("daily") or []
    start = weather.get("todayIndex", 0) + 1
    out = []
    for offset, day in enumerate(daily[start:start + days], start=1):
        thunder = day.get("weatherCode") in THUNDER_CODES
        scores = {
            "heat": ramp(day.get("heatIndexMaxF"), HEAT_INDEX_F),
            "lightning": max(ramp(day.get("capeMax"), CAPE_JKG), 6.0 if thunder else 0.0),
            "flooding": ramp(day.get("precipIn"), RAIN_24H_IN) if waterway else min(ramp(day.get("precipIn"), RAIN_24H_IN), 8.0),
            "wind": ramp(day.get("gustMaxMph"), GUST_MPH),
            "wildfire": 3.0 if (day.get("humidityMinPct") or 100) < 20 and (day.get("gustMaxMph") or 0) >= 25 else 0.0,
            # Soil dries slowly; heavy rain re-wets it.
            "soil": max(hazards_now.get("soil", 0) * 0.85 ** offset, ramp(day.get("precipIn"), RAIN_24H_IN) * 0.8),
            "wildlife": hazards_now.get("wildlife", 0),
        }
        scores = {key: round(scores[key], 1) for key in HAZARD_KEYS}
        out.append({
            "date": day["date"],
            "hazardIndex": combine(scores),
            "topHazard": max(scores, key=scores.get),
            "hazards": scores,
        })
    return out

"""Nearest USGS stream gauge and its 24-hour water-level change (waterservices.usgs.gov)."""
from datetime import datetime, timezone

from .http import get, haversine_miles

IV_URL = "https://waterservices.usgs.gov/nwis/iv/"
GAGE_HEIGHT = "00065"  # USGS parameter code for gage height, feet
SEARCH_DEGREES = 0.5   # ~35 miles around the site
NAMED_GAUGE_MILES = 40 # a gauge on the site's own waterway wins within this distance
GENERIC_WORDS = {"river", "lake", "bay", "creek", "lagoon", "sound", "ocean", "gulf", "of", "the", "st", "reservoir"}


def waterway_keyword(waterway):
    """Distinctive word of the waterway name, e.g. "Mississippi River" -> "mississippi"."""
    words = [w for w in (waterway or "").lower().replace(".", " ").replace("(", " ").split() if w not in GENERIC_WORDS]
    return words[0] if words else None


def fetch_river(site, previous=None):
    """Latest stage and 24-hour change at the best nearby gauge (reuses the gauge found last time).

    Gauges named after the site's waterway win over closer gauges on side streams."""
    params = {"format": "json", "parameterCd": GAGE_HEIGHT, "period": "P1D", "siteStatus": "active"}
    if previous and previous.get("gaugeId"):
        params["sites"] = previous["gaugeId"]
    else:
        d = SEARCH_DEGREES
        params["bBox"] = f"{site.lng - d:.4f},{site.lat - d:.4f},{site.lng + d:.4f},{site.lat + d:.4f}"
    response = get(IV_URL, params=params, timeout=30)
    fetched = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if response.status_code == 404:  # USGS answers 404 when no gauge matches
        return {"fetchedAt": fetched, "gaugeId": None}
    response.raise_for_status()

    keyword = waterway_keyword(site.waterway)
    best, best_rank = None, None
    for series in response.json().get("value", {}).get("timeSeries", []):
        info = series["sourceInfo"]
        location = info["geoLocation"]["geogLocation"]
        no_data = series.get("variable", {}).get("noDataValue")
        readings = [v for v in series["values"][0]["value"] if v.get("value") not in (None, "") and float(v["value"]) != no_data]
        if not readings:
            continue
        distance = haversine_miles(site.lat, site.lng, location["latitude"], location["longitude"])
        latest, first = float(readings[-1]["value"]), float(readings[0]["value"])
        candidate = {
            "gaugeId": info["siteCode"][0]["value"],
            "gaugeName": info["siteName"].title(),
            "distanceMiles": round(distance, 1),
            "stageFt": latest,
            "change24hFt": round(latest - first, 2),
            "observedAt": readings[-1]["dateTime"],
        }
        on_waterway = bool(keyword) and keyword in info["siteName"].lower() and distance <= NAMED_GAUGE_MILES
        rank = (0 if on_waterway else 1, distance)
        if best_rank is None or rank < best_rank:
            best, best_rank = candidate, rank
    return {"fetchedAt": fetched, **(best or {"gaugeId": None})}

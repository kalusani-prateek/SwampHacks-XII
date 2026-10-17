"""Active fires near sites from NASA FIRMS (VIIRS satellite detections, last 24 hours, public files)."""
import csv
import io
import logging
from datetime import datetime, timezone

import numpy as np

from .http import get

log = logging.getLogger(__name__)
FIRMS_FILES = [
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv",
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv",
]


def fetch_detections():
    """All nominal/high-confidence fire detections over the U.S. in the last 24 h: [(lat, lng)]."""
    points = []
    for url in FIRMS_FILES:
        try:
            response = get(url, timeout=60)
            response.raise_for_status()
        except Exception as exc:  # one satellite missing is fine
            log.warning("FIRMS file unavailable (%s): %s", url.rsplit("/", 1)[-1], exc)
            continue
        for row in csv.DictReader(io.StringIO(response.text)):
            if str(row.get("confidence", "")).lower() in ("l", "low"):
                continue
            try:
                points.append((float(row["latitude"]), float(row["longitude"])))
            except (KeyError, ValueError):
                continue
    return points


def nearest_by_site(sites, points):
    """{site_id: {"nearestMiles", "within25mi"}} using vectorized great-circle distances."""
    fetched = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    if not points:
        return {s.id: {"fetchedAt": fetched, "nearestMiles": None, "within25mi": 0} for s in sites}
    fire = np.radians(np.array(points))
    result = {}
    for site in sites:
        lat, lng = np.radians(site.lat), np.radians(site.lng)
        a = np.sin((fire[:, 0] - lat) / 2) ** 2 + np.cos(lat) * np.cos(fire[:, 0]) * np.sin((fire[:, 1] - lng) / 2) ** 2
        miles = 3958.8 * 2 * np.arcsin(np.sqrt(a))
        result[site.id] = {
            "fetchedAt": fetched,
            "nearestMiles": round(float(miles.min()), 1),
            "within25mi": int((miles <= 25).sum()),
        }
    return result

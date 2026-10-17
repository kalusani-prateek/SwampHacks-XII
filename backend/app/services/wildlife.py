"""Dangerous-wildlife sightings near sites from iNaturalist (public observations, free API).

Counts alligators, venomous snakes, black bears and cougars observed within
10 miles in the last 30 days. iNaturalist asks for about one request per
second, so the refresh job pauses between sites.
"""
from datetime import date, datetime, timedelta, timezone

from .http import get

API = "https://api.inaturalist.org/v1"
SPECIES = [
    "Alligator mississippiensis",  # American alligator
    "Crotalus",                    # rattlesnakes
    "Agkistrodon piscivorus",      # cottonmouth
    "Agkistrodon contortrix",      # copperhead
    "Micrurus fulvius",            # eastern coral snake
    "Ursus americanus",            # black bear
    "Puma concolor",               # cougar
]
RADIUS_KM = 16  # ~10 miles
_taxon_ids = []


def taxon_ids():
    """Look up iNaturalist taxon IDs once per process."""
    if not _taxon_ids:
        for name in SPECIES:
            response = get(f"{API}/taxa", params={"q": name, "per_page": 5}, timeout=20)
            response.raise_for_status()
            match = next((t for t in response.json().get("results", []) if t.get("name") == name), None)
            if match:
                _taxon_ids.append(match["id"])
    return list(_taxon_ids)


def fetch_sightings(site, ids):
    response = get(f"{API}/observations", params={
        "lat": round(site.lat, 4),
        "lng": round(site.lng, 4),
        "radius": RADIUS_KM,
        "taxon_id": ",".join(str(i) for i in ids),
        "d1": (date.today() - timedelta(days=30)).isoformat(),
        "order": "desc",
        "order_by": "observed_on",
        "per_page": 5,
    }, timeout=30)
    response.raise_for_status()
    data = response.json()
    recent = []
    for obs in data.get("results", []):
        taxon = obs.get("taxon") or {}
        recent.append({"name": taxon.get("preferred_common_name") or taxon.get("name"), "observedOn": obs.get("observed_on")})
    return {
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "count30d": data.get("total_results", 0),
        "recent": recent,
    }

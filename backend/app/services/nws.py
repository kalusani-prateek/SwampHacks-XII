"""Active National Weather Service alerts for a site (api.weather.gov, free, no key)."""
from datetime import datetime, timezone

from .http import get


def fetch_alerts(site):
    """Watches, warnings and advisories in effect at the site's location."""
    response = get(
        "https://api.weather.gov/alerts/active",
        params={"point": f"{site.lat:.4f},{site.lng:.4f}"},
        headers={"Accept": "application/geo+json"},
        timeout=20,
    )
    response.raise_for_status()
    alerts = []
    for feature in response.json().get("features", []):
        props = feature.get("properties") or {}
        alerts.append({
            "id": props.get("id"),
            "event": props.get("event"),
            "severity": props.get("severity"),
            "headline": props.get("headline"),
            "expires": props.get("ends") or props.get("expires"),
        })
    return {"fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "alerts": alerts}

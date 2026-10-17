"""Weather for every site from Open-Meteo (one request covers all sites).

Free tier: non-commercial use, about 2 calls per site per refresh with the
variables below, so the default hourly refresh uses ~2,800 of the 10,000
daily calls. Set OPEN_METEO_API_KEY to use the commercial endpoint instead.
"""
from datetime import datetime, timezone

from .http import get

FREE_URL = "https://api.open-meteo.com/v1/forecast"
COMMERCIAL_URL = "https://customer-api.open-meteo.com/v1/forecast"

CURRENT = ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation",
           "weather_code", "wind_speed_10m", "wind_gusts_10m"]
HOURLY = ["precipitation", "apparent_temperature", "wind_gusts_10m", "soil_moisture_3_to_9cm", "cape"]
DAILY = ["temperature_2m_max", "apparent_temperature_max", "precipitation_sum", "precipitation_hours",
         "wind_gusts_10m_max", "wind_speed_10m_max", "weather_code", "relative_humidity_2m_min", "cape_max"]


def fetch_all(sites, api_key=""):
    """Return {site_id: weather summary} for the given sites."""
    if not sites:
        return {}
    params = {
        "latitude": ",".join(f"{s.lat:.4f}" for s in sites),
        "longitude": ",".join(f"{s.lng:.4f}" for s in sites),
        "current": ",".join(CURRENT),
        "hourly": ",".join(HOURLY),
        "daily": ",".join(DAILY),
        "past_days": 3,  # the ML hazard model looks at the last 3 days of rain
        "forecast_days": 8,
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "auto",
    }
    url = FREE_URL
    if api_key:
        params["apikey"] = api_key
        url = COMMERCIAL_URL
    response = get(url, params=params, timeout=90)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict):  # a single location comes back as an object, not a list
        data = [data]
    return {site.id: summarize(item) for site, item in zip(sites, data)}


def summarize(item):
    """Keep what scoring needs: current readings, the next 12 hours, the last 24 h of rain, and the daily table."""
    current = item.get("current") or {}
    hourly = item.get("hourly") or {}
    times = hourly.get("time") or []
    now_local = current.get("time") or ""
    # Index of the current hour: the last hourly timestamp at or before "now" (ISO strings sort correctly).
    hour = max((i for i, t in enumerate(times) if t <= now_local), default=0)

    def window(name, start, end):
        values = (hourly.get(name) or [])[max(start, 0):max(end, 0)]
        return [v for v in values if v is not None]

    rain_24h = window("precipitation", hour - 23, hour + 1)
    next_12 = slice(hour, hour + 12)
    soil = (hourly.get("soil_moisture_3_to_9cm") or [None])[hour] if times else None

    daily = item.get("daily") or {}
    days = []
    for i, date in enumerate(daily.get("time") or []):
        def value(name):
            values = daily.get(name) or []
            return values[i] if i < len(values) else None
        days.append({
            "date": date,
            "tempMaxF": value("temperature_2m_max"),
            "heatIndexMaxF": value("apparent_temperature_max"),
            "precipIn": value("precipitation_sum"),
            "precipHours": value("precipitation_hours"),
            "gustMaxMph": value("wind_gusts_10m_max"),
            "windMaxMph": value("wind_speed_10m_max"),
            "weatherCode": value("weather_code"),
            "humidityMinPct": value("relative_humidity_2m_min"),
            "capeMax": value("cape_max"),
        })
    today = now_local[:10]
    today_index = next((i for i, d in enumerate(days) if d["date"] == today), 0)

    def peak(name):
        values = window(name, next_12.start, next_12.stop)
        return max(values) if values else None

    return {
        "fetchedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "timezone": item.get("timezone"),
        "current": {
            "time": now_local,
            "tempF": current.get("temperature_2m"),
            "humidityPct": current.get("relative_humidity_2m"),
            "heatIndexF": current.get("apparent_temperature"),
            "precipIn": current.get("precipitation"),
            "weatherCode": current.get("weather_code"),
            "windMph": current.get("wind_speed_10m"),
            "gustMph": current.get("wind_gusts_10m"),
        },
        "precip24hIn": round(sum(rain_24h), 2) if rain_24h else None,
        "soilMoisture": soil,
        "heatIndexNext12hF": peak("apparent_temperature"),
        "gustNext12hMph": peak("wind_gusts_10m"),
        "capeNext12h": peak("cape"),
        "daily": days,
        "todayIndex": today_index,
    }

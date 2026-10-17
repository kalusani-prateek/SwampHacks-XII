"""Fit the ML hazard model from public history and write ml/hazard_model.json.

    cd backend
    .venv\\Scripts\\python -m ml.fit_hazard_model                        # 2023-2025, ~10 min the first time
    .venv\\Scripts\\python -m ml.fit_hazard_model --years 2022 2023 2024 2025

What it does
1. NOAA Storm Events (NCEI): every reported thunderstorm wind, lightning, hail, tornado,
   flood, heat, high wind, tropical storm and wildfire event in those years.
2. Each site's NWS forecast zone and county (api.weather.gov), for events reported by area.
3. Daily weather at each site from the Open-Meteo historical archive: the same daily values
   the live forecast provides (services/weather.py).
4. A site-day counts as hazardous when such an event was reported within 25 miles of the
   site, or in its forecast zone or county, that day.
5. Logistic regression (numpy): checked on the last year after fitting on the earlier ones,
   compared with the rule-based index on the same weather, then refit on all the years.

Downloads are cached in ml/data/ (git-ignored), so reruns only refit.
"""
import argparse
import csv
import gzip
import json
import math
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import numpy as np
import requests

from app.services.hazard_model import FEATURES, MODEL_PATH, day_features
from app.services.hazards import GUST_MPH, HAZARD_KEYS, HEAT_INDEX_F, RAIN_24H_IN, combine, ramp
from config import BACKEND_DIR, Config

DATA_DIR = BACKEND_DIR / "ml" / "data"
SITES_CSV = BACKEND_DIR / "data" / "sites.csv"
STORM_INDEX = "https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
USER_AGENT = f"PlanIT-Control/1.0 ({Config.CONTACT_EMAIL or 'contact not set'})"

RADIUS_MILES = 25
MAX_EVENT_DAYS = 10  # longer events (heat waves, slow floods) count for their first 10 days
EVENT_TYPES = {
    "Thunderstorm Wind", "Lightning", "Hail", "Tornado", "Flash Flood", "Flood", "Heavy Rain",
    "Coastal Flood", "Storm Surge/Tide", "Excessive Heat", "Heat", "High Wind", "Strong Wind",
    "Tropical Storm", "Tropical Depression", "Hurricane", "Hurricane (Typhoon)", "Wildfire",
    "Debris Flow", "Dust Storm",
}
# Open-Meteo daily variable -> the key services/weather.py uses for the same value.
DAILY = {
    "apparent_temperature_max": "heatIndexMaxF",
    "precipitation_sum": "precipIn",
    "precipitation_hours": "precipHours",
    "wind_gusts_10m_max": "gustMaxMph",
    "wind_speed_10m_max": "windMaxMph",
    "relative_humidity_2m_min": "humidityMinPct",
}
STATE_FIPS = {
    1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT", 10: "DE", 11: "DC", 12: "FL",
    13: "GA", 15: "HI", 16: "ID", 17: "IL", 18: "IN", 19: "IA", 20: "KS", 21: "KY", 22: "LA",
    23: "ME", 24: "MD", 25: "MA", 26: "MI", 27: "MN", 28: "MS", 29: "MO", 30: "MT", 31: "NE",
    32: "NV", 33: "NH", 34: "NJ", 35: "NM", 36: "NY", 37: "NC", 38: "ND", 39: "OH", 40: "OK",
    41: "OR", 42: "PA", 44: "RI", 45: "SC", 46: "SD", 47: "TN", 48: "TX", 49: "UT", 50: "VT",
    51: "VA", 53: "WA", 54: "WV", 55: "WI", 56: "WY", 72: "PR",
}


def log(message):
    print(message, flush=True)


# --- Downloads (cached) -------------------------------------------------------

def download(url, path):
    """Fetch url into path unless it's already there."""
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(partial, "wb") as f:
            for chunk in response.iter_content(1 << 16):
                f.write(chunk)
    partial.replace(path)
    return path


def storm_files(years):
    """The newest NOAA Storm Events details file for each year."""
    listing, paths = None, []
    for year in years:
        path = DATA_DIR / "raw" / f"storm_details_{year}.csv.gz"
        if not path.exists():
            if listing is None:
                response = requests.get(STORM_INDEX, timeout=60)
                response.raise_for_status()
                listing = response.text
            names = sorted(set(re.findall(rf"StormEvents_details-ftp_v1\.0_d{year}_c\d+\.csv\.gz", listing)))
            if not names:
                sys.exit(f"NOAA hasn't published Storm Events for {year} yet.")
            log(f"Downloading {names[-1]}")
            download(STORM_INDEX + names[-1], path)
        paths.append(path)
    return paths


def load_sites():
    with open(SITES_CSV, newline="", encoding="utf-8") as f:
        return [{"id": r["id"], "lat": float(r["lat"]), "lng": float(r["lng"])} for r in csv.DictReader(f)]


def site_areas(sites):
    """{site_id: [forecast zone, county]} as NWS ids, e.g. ["FLZ173", "FLC086"]."""
    path = DATA_DIR / "site_areas.json"
    areas = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for site in sites:
        if site["id"] in areas:
            continue
        response = requests.get(f"https://api.weather.gov/points/{site['lat']:.4f},{site['lng']:.4f}",
                                headers={"User-Agent": USER_AGENT, "Accept": "application/geo+json"}, timeout=30)
        response.raise_for_status()
        props = response.json()["properties"]
        areas[site["id"]] = [props["forecastZone"].rsplit("/", 1)[-1], props["county"].rsplit("/", 1)[-1]]
        time.sleep(0.2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(areas, indent=1), encoding="utf-8")
    return areas


def site_weather(site, start, end):
    """Daily weather at a site from the Open-Meteo archive, as weather.summarize()-style dicts."""
    path = DATA_DIR / "weather" / f"{site['id']}_{start}_{end}.json"
    if not path.exists():
        params = {
            "latitude": f"{site['lat']:.4f}", "longitude": f"{site['lng']:.4f}",
            "start_date": start, "end_date": end, "daily": ",".join(DAILY),
            "temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "precipitation_unit": "inch",
            "timezone": "auto",
        }
        for _ in range(6):
            response = requests.get(ARCHIVE_URL, params=params, timeout=120)
            if response.status_code != 429:
                break
            log("    Open-Meteo rate limit reached: waiting a minute")
            time.sleep(65)
        response.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(response.text, encoding="utf-8")
        time.sleep(8)  # years of data count as many API calls; stay under the per-minute limit
    daily = json.loads(path.read_text(encoding="utf-8"))["daily"]
    return [{"date": day, **{key: daily[name][i] for name, key in DAILY.items()}}
            for i, day in enumerate(daily["time"])]


# --- Which site-days were hazardous -------------------------------------------

def event_days(row):
    """Local dates a Storm Events report covers (at most MAX_EVENT_DAYS)."""
    begin = date(int(row["BEGIN_YEARMONTH"][:4]), int(row["BEGIN_YEARMONTH"][4:]), int(row["BEGIN_DAY"]))
    end = date(int(row["END_YEARMONTH"][:4]), int(row["END_YEARMONTH"][4:]), int(row["END_DAY"]))
    span = max(0, min((end - begin).days, MAX_EVENT_DAYS - 1))
    return [(begin + timedelta(days=d)).isoformat() for d in range(span + 1)]


def hazardous_days(storm_paths, sites, areas):
    """{(site_id, "YYYY-MM-DD")}: site-days with a qualifying report nearby or in the site's zone/county."""
    ids = [s["id"] for s in sites]
    lat = np.radians([s["lat"] for s in sites])
    lng = np.radians([s["lng"] for s in sites])
    by_area = defaultdict(list)  # ("Z", "FL", 173) -> site ids
    for site_id, nws_ids in areas.items():
        for nws_id in nws_ids:
            by_area[(nws_id[2], nws_id[:2], int(nws_id[3:]))].append(site_id)

    def near(event_lat, event_lng):
        a = (np.sin((lat - math.radians(event_lat)) / 2) ** 2
             + np.cos(lat) * math.cos(math.radians(event_lat)) * np.sin((lng - math.radians(event_lng)) / 2) ** 2)
        miles = 3958.8 * 2 * np.arcsin(np.sqrt(a))
        return {ids[i] for i in np.flatnonzero(miles <= RADIUS_MILES)}

    days = set()
    for path in storm_paths:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.DictReader(f):
                if row["EVENT_TYPE"] not in EVENT_TYPES:
                    continue
                points = [(row["BEGIN_LAT"], row["BEGIN_LON"]), (row["END_LAT"], row["END_LON"])]
                points = [(float(a), float(b)) for a, b in points if a and b]
                if points:  # located reports: distance to each site
                    matched = set().union(*(near(a, b) for a, b in points))
                else:  # reports filed for a whole forecast zone or county
                    state = STATE_FIPS.get(int(row["STATE_FIPS"] or 0))
                    matched = by_area.get((row["CZ_TYPE"], state, int(row["CZ_FIPS"] or 0)), [])
                for day in event_days(row) if matched else ():
                    days.update((site_id, day) for site_id in matched)
    return days


# --- Model --------------------------------------------------------------------

def rule_index(day):
    """The rule-based index from the same daily weather (no lightning, river, fire or wildlife data)."""
    scores = dict.fromkeys(HAZARD_KEYS, 0.0)
    scores.update(heat=ramp(day["heatIndexMaxF"], HEAT_INDEX_F), wind=ramp(day["gustMaxMph"], GUST_MPH),
                  flooding=ramp(day["precipIn"], RAIN_24H_IN))
    return combine(scores)


def site_day_rows(sites, years, hazardous):
    """Inputs, outcome, year and rule-based index for every site-day with complete weather."""
    start = (date(min(years), 1, 1) - timedelta(days=3)).isoformat()  # 3 extra days for recent rain
    end = min(date(max(years), 12, 31), date.today() - timedelta(days=6)).isoformat()  # the archive lags ~5 days
    X, y, year, rules = [], [], [], []
    for n, site in enumerate(sites, 1):
        log(f"  [{n}/{len(sites)}] {site['id']}")
        days = site_weather(site, start, end)
        for i, day in enumerate(days):
            if int(day["date"][:4]) not in years:
                continue
            features = day_features(day, days[max(0, i - 3):i], site["lat"], site["lng"])
            if features is None:
                continue
            X.append(features)
            y.append((site["id"], day["date"]) in hazardous)
            year.append(int(day["date"][:4]))
            rules.append(rule_index(day))
    return np.array(X), np.array(y, dtype=float), np.array(year), np.array(rules)


def fit_logistic(X, y, l2=1.0, iterations=100):
    """L2-regularised logistic regression (Newton's method) on standardised inputs."""
    mean, scale = X.mean(axis=0), X.std(axis=0)
    scale[scale == 0] = 1.0
    A = np.hstack([np.ones((len(X), 1)), (X - mean) / scale])
    w = np.zeros(A.shape[1])
    penalty = np.full(A.shape[1], l2)
    penalty[0] = 0.0  # the intercept isn't shrunk
    for _ in range(iterations):
        p = 1 / (1 + np.exp(-np.clip(A @ w, -40, 40)))
        gradient = A.T @ (p - y) + penalty * w
        hessian = (A * (p * (1 - p))[:, None]).T @ A + np.diag(penalty)
        step = np.linalg.solve(hessian, gradient)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return {"mean": mean.tolist(), "scale": scale.tolist(), "intercept": float(w[0]), "coef": w[1:].tolist()}


def probabilities(model, X):
    z = model["intercept"] + ((X - np.array(model["mean"])) / np.array(model["scale"])) @ np.array(model["coef"])
    return 1 / (1 + np.exp(-np.clip(z, -40, 40)))


def roc_auc(y, score):
    """Chance that a random hazardous day scores above a random calm one (ties count half)."""
    y = np.asarray(y, dtype=bool)
    _, inverse, counts = np.unique(score, return_inverse=True, return_counts=True)
    ends = np.cumsum(counts)
    ranks = ((ends - counts + 1 + ends) / 2.0)[inverse]
    positives, negatives = int(y.sum()), int((~y).sum())
    return float((ranks[y].sum() - positives * (positives + 1) / 2) / (positives * negatives))


def main():
    parser = argparse.ArgumentParser(description="Fit the ML hazard model (writes ml/hazard_model.json).")
    parser.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025])
    years = sorted(set(parser.parse_args().years))
    if len(years) < 2:
        sys.exit("Give at least two years: the last one is held back to check the model.")

    sites = load_sites()
    log(f"{len(sites)} sites, {years[0]}-{years[-1]}")
    storm_paths = storm_files(years)
    areas = site_areas(sites)
    hazardous = hazardous_days(storm_paths, sites, areas)
    log(f"{len(hazardous):,} site-days with a qualifying NOAA report")
    log("Daily weather from the Open-Meteo archive (cached after the first run):")
    X, y, year, rules = site_day_rows(sites, set(years), hazardous)
    log(f"{len(y):,} site-days, {y.mean():.1%} hazardous")

    test_year = years[-1]
    fit_rows, test_rows = year < test_year, year == test_year
    p = probabilities(fit_logistic(X[fit_rows], y[fit_rows]), X[test_rows])
    check = {
        "fitYears": years[:-1],
        "testYear": test_year,
        "auc": round(roc_auc(y[test_rows], p), 3),
        "rulesAuc": round(roc_auc(y[test_rows], rules[test_rows]), 3),
        "brier": round(float(np.mean((p - y[test_rows]) ** 2)), 4),
        "baselineBrier": round(float(np.mean((y[fit_rows].mean() - y[test_rows]) ** 2)), 4),
    }
    log(f"Check on {test_year}: AUC {check['auc']} (rules on the same weather: {check['rulesAuc']}); "
        f"Brier {check['brier']} (always guessing the average: {check['baselineBrier']})")

    model = {
        "features": FEATURES,
        **fit_logistic(X, y),
        "fittedAt": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "target": ("A NOAA Storm Events report within 25 mi of the site, or in its NWS forecast zone or county, "
                   "that day: thunderstorm wind, lightning, hail, tornado, flood, heat, high wind, tropical "
                   "storm or wildfire"),
        "data": {"years": years, "sites": len(sites), "siteDays": int(len(y)),
                 "hazardousShare": round(float(y.mean()), 4)},
        "check": check,
    }
    MODEL_PATH.write_text(json.dumps(model, indent=2) + "\n", encoding="utf-8")
    log(f"Wrote {MODEL_PATH.relative_to(BACKEND_DIR)}")
    for name, coef in sorted(zip(FEATURES, model["coef"]), key=lambda item: -abs(item[1])):
        log(f"  {name:20s} {coef:+.3f}")


if __name__ == "__main__":
    main()

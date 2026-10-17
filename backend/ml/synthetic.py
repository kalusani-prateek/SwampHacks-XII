"""Realistic synthetic site-days for training.

The model must never train on the 50 real sample locations (that is exactly
the overfitting the user wants to avoid), so training data is generated here
from joint distributions with domain-realistic correlations:

    stormy days -> heavy rain, high wind, humidity, nearby lightning
    heavy rain  -> soil moisture spikes (AR(1) saturation), river stage rise
    near-river wetland sites -> high moisture baseline, flood exposure
    wildlife sightings -> Poisson by site archetype (swamp = alligators...)

Labels come from the expert rules (ml/rules.py) computed on the COMPLETE row
plus Gaussian noise, so the model learns the scoring surface, not the noise.
Missing values are injected AFTER labeling so training data mimics real API
gaps and the model learns to score incomplete payloads.
"""

import math

import numpy as np
import pandas as pd

from ml import rules

LABEL_SIGMA = 0.35  # noise on synthetic labels only (never on real labels)

# (archetype, probability) mixture for site generation.
ARCHETYPES = [("wetland", 0.30), ("forest", 0.30), ("grassland", 0.20), ("urban", 0.20)]

# Most-severe species threat level pools per archetype (alligator 5, bear 4.5,
# venomous snake 4, boar 3.5, deer 2).
SPECIES_POOLS = {
    "wetland": [5.0, 4.0, 3.5],
    "forest": [4.5, 4.0, 3.5],
    "grassland": [4.0, 3.5, 2.0],
    "urban": [3.5, 2.0],
}
WILDLIFE_BASE = {"wetland": 2.0, "forest": 1.5, "grassland": 1.0, "urban": 0.4}

# Field -> probability the field is missing in a row (injected post-label).
MISSING_RATES = {
    "temp_min_c": 0.10,
    "visibility_km": 0.15,
    "elevation_above_river_m": 0.15,
    "precip_intensity_max_mmh": 0.10,
    "minutes_since_last_strike_min": 0.35,
}
DEFAULT_MISSING = 0.03


def generate_sites(n, rng):
    """Static site attributes: geography, baselines, hazard proneness."""
    names = [a for a, _ in ARCHETYPES]
    probs = [p for _, p in ARCHETYPES]
    sites = []
    for i in range(n):
        archetype = rng.choice(names, p=probs)
        r = rng.random()
        if r < 0.40:      # close to a river (flood-prone)
            dist_m = rng.uniform(50, 2000)
            elev = rng.uniform(0.5, 3.0)
        elif r < 0.70:    # mid-distance
            dist_m = rng.uniform(2000, 8000)
            elev = rng.uniform(1.0, 15.0)
        else:             # far
            dist_m = rng.uniform(8000, 50000)
            elev = rng.uniform(3.0, 60.0)
        is_wetland = rng.random() < (0.75 if dist_m < 2000 else 0.15)
        sites.append({
            "site_id": f"site_{i}",
            "archetype": str(archetype),
            "distance_to_river_m": round(dist_m, 1),
            "elevation_above_river_m": round(elev, 2),
            "is_wetland": bool(is_wetland),
            "soil_eq": rng.uniform(65, 90) if is_wetland else rng.uniform(30, 55),
            "storm_proneness": min(0.55, rng.uniform(0.05, 0.45) + (0.10 if is_wetland else 0.0)),
            "wildlife_density": WILDLIFE_BASE[archetype] * rng.uniform(0.5, 1.5),
            "species_pool": SPECIES_POOLS[archetype],
            "heat_offset": rng.uniform(-8.0, 6.0),
            "latitude": round(rng.uniform(24.5, 31.0), 4),
            "longitude": round(rng.uniform(-87.5, -80.0), 4),
        })
    return sites


def _storm_day(site, rng, wet_spell=False):
    """Correlated conditions on a storm day."""
    # ~10% are dry storms: close lightning, little rain, dry air. Real
    # phenomenon (dry lightning) and it teaches the model that a nearby
    # strike is dangerous even when every other condition looks calm.
    if rng.random() < 0.10:
        lightning_km = float(np.clip(rng.gamma(2.0, 6.0) + 1.0, 1.0, 150.0))
        minutes = rng.uniform(0, 90) if lightning_km < 30 else math.nan
        return (rng.uniform(0, 3),                    # rain
                rng.uniform(15, 50),                  # wind
                float(np.clip(rng.normal(45, 8), 20, 90)),  # humidity
                29.0 + site["heat_offset"] + rng.normal(0, 3),  # temp neutral
                lightning_km, minutes,
                rng.random() < 0.15,                  # severe
                rng.uniform(8, 18))                    # visibility

    extreme = rng.random() < 0.07
    rain = rng.gamma(2.0, 12.0)
    if extreme:
        rain *= rng.uniform(2.5, 5.0)
    if wet_spell:
        rain *= 1.6  # multi-day rain regimes dump more per storm
    rain = min(rain, 450.0)
    wind = rng.uniform(60, 110) if extreme else rng.uniform(30, 75)
    humidity = float(np.clip(rng.normal(80 + (8 if wet_spell else 0), 8), 30, 98))
    temp = 29.0 + site["heat_offset"] + rng.normal(-3, 3.5)
    lightning_km = float(np.clip(rng.gamma(2.0, 8.0) + 2.0, 1.0, 150.0))
    minutes = rng.uniform(0, 120) if lightning_km < 30 else math.nan
    p_severe = 0.12 + (0.25 if rain > 50 else 0.0) + (0.20 if wind > 60 else 0.0)
    severe = rng.random() < min(p_severe, 0.5)
    visibility = rng.uniform(2, 10)
    return rain, wind, humidity, temp, lightning_km, minutes, severe, visibility


def _clear_day(site, rng):
    """Correlated conditions on a calm day."""
    if rng.random() < 0.06:
        rain = rng.uniform(0, 4)
    else:
        rain = 0.0
    wind = rng.uniform(3, 25)
    humidity = float(np.clip(rng.normal(55, 10), 20, 95))
    temp = 29.0 + site["heat_offset"] + rng.normal(0, 2)
    lightning_km = rng.uniform(60, 130)
    minutes = math.nan
    severe = rng.random() < 0.01
    visibility = rng.uniform(0.2, 1.2) if rng.random() < 0.10 else rng.uniform(8, 20)
    return rain, wind, humidity, temp, lightning_km, minutes, severe, visibility


def generate_site_rows(site, days, rng, sigma):
    """One site -> `days` labeled canonical rows (complete, pre-masking)."""
    rows = []
    moisture = site["soil_eq"]
    recent_rain = []  # rolling precip history for rain_prev_72h_mm
    dist_km = site["distance_to_river_m"] / 1000.0
    spell_left = 0  # days remaining in a wet spell

    for day in range(days):
        # Wet spells: multi-day periods of elevated storminess and rain
        if spell_left == 0 and rng.random() < 0.06:
            spell_left = int(rng.integers(3, 6))  # 3-5 days
        wet_spell = spell_left > 0
        if wet_spell:
            spell_left -= 1
        p_storm = 0.65 if wet_spell else min(0.50, 0.12 + 0.6 * site["storm_proneness"])
        stormy = rng.random() < p_storm
        if stormy:
            rain, wind, rh, temp, lkm, minutes, severe, vis = _storm_day(site, rng, wet_spell)
        else:
            rain, wind, rh, temp, lkm, minutes, severe, vis = _clear_day(site, rng)

        # soil saturation: AR(1) toward site equilibrium, rain spikes it up
        moisture = float(np.clip(0.75 * moisture + 0.25 * site["soil_eq"]
                                 + 0.10 * rain + rng.normal(0, 2), 0, 100))

        rain72 = sum(recent_rain[-3:])
        stage = float(np.clip(0.15 + 0.004 * rain72 * math.exp(-dist_km / 6.0)
                              + rng.normal(0, 0.08), -1.0, 6.0))
        if stormy and rain72 > 120 and dist_km < 2.0:
            stage += rng.uniform(0.8, 2.2)  # river already swollen + local downpour

        s24 = int(rng.poisson(site["wildlife_density"] * (1.3 if stormy else 0.9)))
        s7 = s24 + int(rng.poisson(site["wildlife_density"] * 5))
        threat = float(rng.choice(site["species_pool"])) if s7 > 0 else math.nan

        row = {
            "site_id": site["site_id"],
            "forecast_date": f"2026-{((day // 28) % 12) + 1:02d}-{(day % 28) + 1:02d}",
            "latitude": site["latitude"],
            "longitude": site["longitude"],
            "temp_max_c": round(temp, 1),
            "temp_min_c": round(temp - abs(rng.normal(8, 2)), 1),
            "relative_humidity_pct": round(rh, 0),
            "wind_max_kmh": round(wind, 0),
            "precip_total_mm": round(rain, 1),
            "precip_intensity_max_mmh": round(min(rain / rng.uniform(1.5, 4.0), 150.0), 1),
            "severe_weather_flag": bool(severe),
            "visibility_km": round(vis, 1),
            "lightning_min_distance_km": round(lkm, 1),
            "minutes_since_last_strike_min": minutes,
            "rain_prev_72h_mm": round(rain72, 1),
            "soil_moisture_pct": round(moisture, 1),
            "river_stage_above_normal_m": round(stage, 2),
            "distance_to_river_m": site["distance_to_river_m"],
            "elevation_above_river_m": site["elevation_above_river_m"],
            "is_wetland": site["is_wetland"],
            "wildlife_sightings_24h": s24,
            "wildlife_sightings_7d": s7,
            "wildlife_max_threat_level": threat,
            "archetype": site["archetype"],
        }
        expert = rules.score_site(row)["index"]
        label = expert if sigma is None else expert + rng.normal(0, sigma)
        row["hazard_label"] = round(float(np.clip(label, 0.0, 10.0)), 4)
        rows.append(row)
        recent_rain.append(rain)
    return rows


def inject_missing(rows, rng):
    """Mask fields post-labeling so training mimics incomplete API payloads."""
    for row in rows:
        for field, rate in MISSING_RATES.items():
            if rng.random() < rate:
                row[field] = math.nan
        for field in ("temp_max_c", "relative_humidity_pct", "wind_max_kmh",
                      "precip_total_mm", "severe_weather_flag", "visibility_km",
                      "lightning_min_distance_km", "rain_prev_72h_mm",
                      "soil_moisture_pct", "river_stage_above_normal_m",
                      "distance_to_river_m", "elevation_above_river_m", "is_wetland",
                      "wildlife_sightings_24h", "wildlife_sightings_7d",
                      "wildlife_max_threat_level", "precip_intensity_max_mmh",
                      "temp_min_c"):
            if rng.random() < DEFAULT_MISSING:
                row[field] = math.nan
    return rows


def make_dataset(n_train_sites=220, n_eval_sites=40, days=60, seed=42, sigma=LABEL_SIGMA):
    """(train_df, eval_df) with disjoint sites; eval labels are noise-free."""
    rng = np.random.default_rng(seed)

    train_rows = []
    for site in generate_sites(n_train_sites, rng):
        train_rows.extend(generate_site_rows(site, days, rng, sigma))
    inject_missing(train_rows, rng)

    eval_rows = []
    for site in generate_sites(n_eval_sites, rng):
        eval_rows.extend(generate_site_rows(site, days, rng, None))  # noise-free labels

    return pd.DataFrame(train_rows), pd.DataFrame(eval_rows)

"""Expert hazard scorer — the label source for training and the runtime
sub-score / hard-rule engine.

Industry-safety-style formulas (NWS heat-index breakpoints, the 10-mile
lightning rule, flood exposure = rain x river proximity x soil saturation).
Every function is NaN-tolerant with the neutral defaults documented below;
missing data never raises, it only lowers confidence (surfaced upstream as
input_issues).

Neutral defaults when a field is missing:
    temp/heat index -> heat 0        wind -> 0            severe flag -> False
    visibility/intensity -> no term lightning dist -> 6.0 if severe else 2.0
    river stage -> 0 term           river distance -> exposure 0.2
    soil moisture -> 60% (flood)    soil moisture -> 0 (soil score)
    elevation -> no flood boost     wildlife counts/threat -> 0
"""

import math

from ml.schema import LIGHTNING_NO_WORK_KM, NO_WORK_WINDOW_MIN, BANDS, compute_heat_index_c

# Aggregation: a single extreme category alone must be able to drive the
# index to ~8+ (e.g. lightning within 10 miles), while consistently bad
# conditions across many categories should also rank high.
MAX_WEIGHT = 0.8
MEAN_WEIGHT = 0.2


def _num(c, key, default=None):
    v = c.get(key)
    if v is None:
        return default
    try:
        v = float(v)
    except (TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def _flag(c, key):
    v = c.get(key)
    return v is True


def _clip(x, lo=0.0, hi=10.0):
    if x is None:
        return None
    return max(lo, min(hi, x))


def _piecewise(x, points):
    """Linear interpolation over sorted [(x, y)] breakpoints, flat outside."""
    if x is None:
        return None
    if x <= points[0][0]:
        return points[0][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x <= x1:
            if x1 == x0:
                return y1
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return points[-1][1]


def heat_score(c):
    hi = compute_heat_index_c(_num(c, "temp_max_c"), _num(c, "relative_humidity_pct"))
    if hi is None:
        return 0.0
    return _piecewise(hi, [(26.0, 0.0), (32.0, 3.0), (40.0, 6.0),
                           (46.0, 8.5), (54.0, 10.0)]) or 0.0


def weather_score(c):
    wind = _num(c, "wind_max_kmh", 0.0)
    score = _piecewise(wind, [(0.0, 0.0), (25.0, 0.0), (60.0, 4.0),
                              (90.0, 7.5), (120.0, 10.0)]) or 0.0
    if _flag(c, "severe_weather_flag"):
        score += 2.5
    vis = _num(c, "visibility_km")
    if vis is not None:
        score += 2.0 * _clip((1.5 - vis) / 1.5, 0.0, 1.0)
    intensity = _num(c, "precip_intensity_max_mmh")
    if intensity is not None:
        score += 2.0 * _clip((intensity - 15.0) / 40.0, 0.0, 1.0)
    return _clip(score)


def lightning_score(c):
    d = _num(c, "lightning_min_distance_km")
    if d is None:
        return 6.0 if _flag(c, "severe_weather_flag") else 2.0
    if d <= LIGHTNING_NO_WORK_KM:
        return 10.0
    if d >= 60.0:
        return 0.0
    return 10.0 * (60.0 - d) / (60.0 - LIGHTNING_NO_WORK_KM)


def flood_score(c):
    rain = _num(c, "precip_total_mm", 0.0)
    rain_term = _piecewise(rain, [(0.0, 0.0), (5.0, 0.0), (25.0, 2.0),
                                  (50.0, 4.5), (100.0, 7.5), (150.0, 10.0)]) or 0.0
    ant = _num(c, "rain_prev_72h_mm", 0.0)
    ant_term = _clip(ant / 200.0 * 10.0)
    stage = _num(c, "river_stage_above_normal_m")
    stage_term = _clip((stage - 0.5) / 3.0 * 10.0) if stage is not None else 0.0
    base = 0.45 * rain_term + 0.25 * ant_term + 0.30 * stage_term

    dist_m = _num(c, "distance_to_river_m")
    exposure = 0.2 if dist_m is None else math.exp(-(dist_m / 1000.0) / 4.0)
    elev = _num(c, "elevation_above_river_m")
    if elev is not None:
        exposure = min(1.0, exposure * (1.0 + 0.6 * _clip((3.0 - elev) / 3.0, 0.0, 1.0)))

    moisture = _num(c, "soil_moisture_pct", 60.0)
    sat = moisture / 100.0

    return _clip(base * (0.35 + 0.65 * exposure) * (0.5 + 0.5 * sat))


def soil_score(c):
    moisture = _num(c, "soil_moisture_pct")
    if moisture is None:
        return 0.0
    score = _piecewise(moisture, [(0.0, 0.0), (55.0, 0.0), (75.0, 3.0),
                                  (90.0, 6.0), (100.0, 8.0)]) or 0.0
    wind = _num(c, "wind_max_kmh", 0.0)
    if moisture >= 80.0 and wind >= 60.0:
        score += 2.0  # saturated ground + high wind -> treefall/equipment risk
    return _clip(score)


def wildlife_score(c):
    threat = _num(c, "wildlife_max_threat_level")
    if threat is None or threat <= 0:
        return 0.0
    s24 = _num(c, "wildlife_sightings_24h", 0.0)
    s7 = _num(c, "wildlife_sightings_7d", s24)
    base = 2.0 * threat
    freq = _clip(math.log1p(s7) / math.log1p(10.0), 0.0, 1.0)
    recency = _clip((s24 + 0.5 * (s7 - s24)) / 5.0, 0.0, 1.0)
    return _clip(base * (0.5 + 0.5 * freq) * (0.4 + 0.6 * recency))


def aggregate(sub_scores):
    """0.8 * max + 0.2 * mean — one extreme category alone reaches 8.0+."""
    values = [v for v in sub_scores.values() if v is not None]
    if not values:
        return 0.0
    return _clip(MAX_WEIGHT * max(values) + MEAN_WEIGHT * sum(values) / len(values))


def band(index):
    """BANDS is [(lower_edge, label)] — the band whose edge index exceeds."""
    result = BANDS[0][1]
    for edge, label in BANDS:
        if index >= edge:
            result = label
        else:
            break
    return result


def work_restriction(c):
    """README rule: a strike within 10 miles means 30 minutes of no work."""
    d = _num(c, "lightning_min_distance_km")
    if d is None or d > LIGHTNING_NO_WORK_KM:
        return False, None
    minutes = _num(c, "minutes_since_last_strike_min")
    if minutes is not None and minutes > NO_WORK_WINDOW_MIN:
        return False, None
    return True, (f"Lightning strike within 10 mi ({LIGHTNING_NO_WORK_KM:.2f} km) "
                  f"— {NO_WORK_WINDOW_MIN:.0f}-minute no-work rule in effect.")


def score_site(c):
    """Canonical site-day dict -> expert hazard report (0-10 index)."""
    subs = {
        "weather": weather_score(c),
        "heat": heat_score(c),
        "lightning": lightning_score(c),
        "flood": flood_score(c),
        "soil": soil_score(c),
        "wildlife": wildlife_score(c),
    }
    index = aggregate(subs)
    restricted, reason = work_restriction(c)
    return {
        "index": round(index, 2),
        "band": band(index),
        "sub_scores": {k: round(v, 2) for k, v in subs.items()},
        "work_restricted": restricted,
        "restriction_reason": reason,
    }


def score_batch(rows):
    return [score_site(c) for c in rows]

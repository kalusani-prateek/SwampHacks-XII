"""Canonical input contract for the hazard-index model.

This module is the single seam between the outside world (weather APIs,
the Flask app, the synthetic generator) and the model:

    raw dict -> normalize() -> canonical dict -> build_features() -> model matrix

When the real API format arrives, add one `from_<provider>(payload)`
function that maps the provider payload to canonical field names; nothing
else in the pipeline changes.
"""

import math
from collections.abc import Mapping

import numpy as np
import pandas as pd

# 10 miles in km — a strike this close triggers the 30-minute no-work rule.
LIGHTNING_NO_WORK_KM = 16.09
NO_WORK_WINDOW_MIN = 30.0

# Hazard bands for the admin UI.
BANDS = [(0.0, "low"), (2.5, "moderate"), (5.0, "high"), (7.5, "critical")]
BAND_EDGES = [2.5, 5.0, 7.5]

CATEGORIES = ["weather", "heat", "lightning", "flood", "soil", "wildlife"]

# Raw field spec: name -> (python type, (min, max) or None)
RAW_FIELDS = {
    "site_id": (str, None),
    "forecast_date": (str, None),
    "latitude": (float, (-90.0, 90.0)),
    "longitude": (float, (-180.0, 180.0)),
    "temp_max_c": (float, (-10.0, 55.0)),
    "temp_min_c": (float, (-25.0, 40.0)),
    "relative_humidity_pct": (float, (0.0, 100.0)),
    "wind_max_kmh": (float, (0.0, 250.0)),
    "precip_total_mm": (float, (0.0, 500.0)),
    "precip_intensity_max_mmh": (float, (0.0, 150.0)),
    "severe_weather_flag": (bool, None),
    "visibility_km": (float, (0.05, 25.0)),
    "lightning_min_distance_km": (float, (0.0, 150.0)),
    "minutes_since_last_strike_min": (float, (0.0, 10080.0)),
    "rain_prev_72h_mm": (float, (0.0, 600.0)),
    "soil_moisture_pct": (float, (0.0, 100.0)),
    "river_stage_above_normal_m": (float, (-2.0, 8.0)),
    "distance_to_river_m": (float, (0.0, 50000.0)),
    "elevation_above_river_m": (float, (0.0, 200.0)),
    "is_wetland": (bool, None),
    "wildlife_sightings_24h": (float, (0.0, 50.0)),
    "wildlife_sightings_7d": (float, (0.0, 200.0)),
    "wildlife_max_threat_level": (float, (0.0, 5.0)),
}

_TRUE_STRINGS = {"true", "yes", "1", "y", "t"}
_FALSE_STRINGS = {"false", "no", "0", "n", "f"}


def _to_float(value, lo_hi, issues, key):
    """Coerce to float; NaN on failure; clamp to range with an issue note."""
    if value is None:
        return float("nan")
    try:
        x = float(value)
    except (TypeError, ValueError):
        issues.append(f"{key}: could not interpret {value!r} as a number")
        return float("nan")
    if not math.isfinite(x):
        return float("nan")
    if lo_hi is not None:
        lo, hi = lo_hi
        if x < lo:
            issues.append(f"{key}: {x:g} below expected range, clamped to {lo:g}")
            x = lo
        elif x > hi:
            issues.append(f"{key}: {x:g} above expected range, clamped to {hi:g}")
            x = hi
    return x


def _to_bool(value, issues, key):
    """Coerce to bool; NaN (treated as False by features) on failure."""
    if value is None:
        return float("nan")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in _TRUE_STRINGS:
            return True
        if s in _FALSE_STRINGS:
            return False
    issues.append(f"{key}: could not interpret {value!r} as a boolean")
    return float("nan")


def normalize(raw):
    """Map an arbitrary payload dict onto the canonical schema.

    Unknown keys are ignored (noted in issues). Missing keys become NaN.
    Returns a dict with every RAW_FIELDS key present plus `_issues` (list of
    human-readable strings for the UI) — never raises on bad input.
    """
    if not isinstance(raw, Mapping):
        raise TypeError(f"expected a mapping, got {type(raw).__name__}")

    issues = []
    canonical = {}
    unknown = [k for k in raw if k not in RAW_FIELDS and not k.startswith("_")]
    if unknown:
        issues.append(f"ignored unknown fields: {', '.join(sorted(map(str, unknown)))}")

    for key, (typ, lo_hi) in RAW_FIELDS.items():
        if key not in raw:
            canonical[key] = "" if typ is str else float("nan")
            continue
        value = raw[key]
        if typ is str:
            canonical[key] = "" if value is None else str(value)
        elif typ is bool:
            canonical[key] = _to_bool(value, issues, key)
        else:
            canonical[key] = _to_float(value, lo_hi, issues, key)

    if not canonical["site_id"]:
        canonical["site_id"] = "unknown"
        issues.append("site_id missing")
    canonical["_issues"] = issues
    return canonical


def compute_heat_index_c(temp_c, rh_pct):
    """NWS Rothfusz heat index (°C out); NaN if either input is NaN.

    Uses the simple formula below 80 °F average and applies the standard
    low-RH / high-RH adjustments above it.
    """
    if temp_c is None or rh_pct is None:
        return float("nan")
    if isinstance(temp_c, float) and math.isnan(temp_c):
        return float("nan")
    if isinstance(rh_pct, float) and math.isnan(rh_pct):
        return float("nan")
    if rh_pct < 0 or rh_pct > 100:
        return float("nan")

    t_f = temp_c * 9.0 / 5.0 + 32.0
    rh = rh_pct
    hi_simple = 0.5 * (t_f + 61.0 + (t_f - 68.0) * 1.2 + rh * 0.094)
    if (hi_simple + t_f) / 2.0 < 80.0:
        return (hi_simple - 32.0) * 5.0 / 9.0

    hi = (-42.379 + 2.04901523 * t_f + 10.14333127 * rh - 0.22475541 * t_f * rh
          - 0.00683783 * t_f * t_f - 0.05481717 * rh * rh + 0.00122874 * t_f * t_f * rh
          + 0.00085282 * t_f * rh * rh - 0.00000199 * t_f * t_f * rh * rh)
    if rh < 13 and 80.0 <= t_f <= 112.0:
        hi -= ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
    elif rh > 85 and 80.0 <= t_f <= 87.0:
        hi += ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)
    return (hi - 32.0) * 5.0 / 9.0


def _num(c, key):
    v = c.get(key, float("nan"))
    try:
        v = float(v)
    except (TypeError, ValueError):
        return float("nan")
    return v if math.isfinite(v) else float("nan")


def _bool01(c, key):
    v = c.get(key)
    if isinstance(v, bool):
        return 1.0 if v else 0.0
    return float("nan")


def _flood_exposure(c):
    d_km = _num(c, "distance_to_river_m") / 1000.0
    if math.isnan(d_km):
        return float("nan")
    return math.exp(-d_km / 4.0)


def _lightning_within(c):
    d = _num(c, "lightning_min_distance_km")
    if math.isnan(d):
        return 0.0
    return 1.0 if d <= LIGHTNING_NO_WORK_KM else 0.0


# (name, builder, monotonic_cst, category) — order fixes the model matrix.
# +1 hazard rises with the feature, -1 falls, 0 unconstrained.
FEATURE_SPEC = [
    ("temp_max_c", lambda c: _num(c, "temp_max_c"), 1, "heat"),
    ("temp_min_c", lambda c: _num(c, "temp_min_c"), 1, "heat"),
    ("relative_humidity_pct", lambda c: _num(c, "relative_humidity_pct"), 0, "heat"),
    ("heat_index_c", lambda c: compute_heat_index_c(_num(c, "temp_max_c"),
                                                    _num(c, "relative_humidity_pct")), 1, "heat"),
    ("wind_max_kmh", lambda c: _num(c, "wind_max_kmh"), 1, "weather"),
    ("precip_total_mm", lambda c: _num(c, "precip_total_mm"), 1, "weather"),
    ("precip_intensity_max_mmh", lambda c: _num(c, "precip_intensity_max_mmh"), 1, "weather"),
    ("severe_weather_flag", lambda c: _bool01(c, "severe_weather_flag"), 1, "weather"),
    ("visibility_km", lambda c: _num(c, "visibility_km"), -1, "weather"),
    ("lightning_min_distance_km", lambda c: _num(c, "lightning_min_distance_km"), -1, "lightning"),
    ("lightning_within_10km", _lightning_within, 1, "lightning"),
    ("rain_prev_72h_mm", lambda c: _num(c, "rain_prev_72h_mm"), 1, "flood"),
    ("soil_moisture_pct", lambda c: _num(c, "soil_moisture_pct"), 1, "soil"),
    ("river_stage_above_normal_m", lambda c: _num(c, "river_stage_above_normal_m"), 1, "flood"),
    ("distance_to_river_km", lambda c: _num(c, "distance_to_river_m") / 1000.0, -1, "flood"),
    ("flood_exposure", _flood_exposure, 1, "flood"),
    ("flood_exposure_tight", lambda c: math.exp(-_num(c, "distance_to_river_m") / 1000.0 / 1.0), 1, "flood"),
    ("rain_x_exposure", lambda c: _num(c, "precip_total_mm") * _flood_exposure(c), 1, "flood"),
    ("stage_x_exposure", lambda c: _num(c, "river_stage_above_normal_m") * _flood_exposure(c), 1, "flood"),
    ("elevation_above_river_m", lambda c: _num(c, "elevation_above_river_m"), -1, "flood"),
    ("is_wetland", lambda c: _bool01(c, "is_wetland"), 0, "soil"),
    ("wildlife_sightings_24h", lambda c: _num(c, "wildlife_sightings_24h"), 1, "wildlife"),
    ("wildlife_sightings_7d", lambda c: _num(c, "wildlife_sightings_7d"), 1, "wildlife"),
    ("wildlife_max_threat_level", lambda c: _num(c, "wildlife_max_threat_level"), 1, "wildlife"),
]

FEATURE_NAMES = [name for name, _, _, _ in FEATURE_SPEC]
MONOTONIC_CST = [cst for _, _, cst, _ in FEATURE_SPEC]


def build_features(canonical):
    """Canonical dict -> {feature name: float}. NaN preserves missingness."""
    return {name: builder(canonical) for name, builder, _, _ in FEATURE_SPEC}


def build_feature_matrix(rows):
    """Iterable of canonical dicts -> model matrix (float64, fixed columns)."""
    records = [build_features(r) for r in rows]
    frame = pd.DataFrame.from_records(records, columns=FEATURE_NAMES)
    return frame.astype("float64")


# Raw-field safe baselines for counterfactual explanations ("what would the
# index be if just this condition were benign?").
SAFE_BASELINE = {
    "temp_max_c": 22.0,
    "temp_min_c": 15.0,
    "relative_humidity_pct": 50.0,
    "wind_max_kmh": 8.0,
    "precip_total_mm": 0.0,
    "precip_intensity_max_mmh": 0.0,
    "severe_weather_flag": False,
    "visibility_km": 15.0,
    "lightning_min_distance_km": 90.0,
    "rain_prev_72h_mm": 0.0,
    "soil_moisture_pct": 45.0,
    "river_stage_above_normal_m": 0.2,
    "distance_to_river_m": 25000.0,
    "elevation_above_river_m": 10.0,
    "is_wetland": False,
    "wildlife_sightings_24h": 0.0,
    "wildlife_sightings_7d": 0.0,
    "wildlife_max_threat_level": 0.0,
}

_DESCRIPTIONS = {
    "temp_max_c": "max temperature {v:.0f}°C",
    "temp_min_c": "overnight low {v:.0f}°C",
    "relative_humidity_pct": "humidity {v:.0f}%",
    "heat_index_c": "heat index {v:.0f}°C",
    "wind_max_kmh": "wind gusts {v:.0f} km/h",
    "precip_total_mm": "rainfall {v:.0f} mm",
    "precip_intensity_max_mmh": "peak rain rate {v:.0f} mm/h",
    "severe_weather_flag": "severe weather warning active",
    "visibility_km": "visibility {v:.1f} km",
    "lightning_min_distance_km": "nearest lightning {v:.0f} km",
    "lightning_within_10km": "lightning within 10 miles",
    "rain_prev_72h_mm": "antecedent rain {v:.0f} mm (72 h)",
    "soil_moisture_pct": "soil moisture {v:.0f}%",
    "river_stage_above_normal_m": "river {v:.1f} m above normal",
    "distance_to_river_km": "river {v:.1f} km away",
    "flood_exposure": "flood exposure {v:.2f}",
    "rain_x_exposure": "rain × river proximity {v:.0f}",
    "stage_x_exposure": "river stage × proximity {v:.1f}",
    "elevation_above_river_m": "site {v:.0f} m above river",
    "is_wetland": "wetland site",
    "wildlife_sightings_24h": "{v:.0f} wildlife sightings (24 h)",
    "wildlife_sightings_7d": "{v:.0f} wildlife sightings (7 d)",
    "wildlife_max_threat_level": "species threat level {v:.1f}/5",
}

# Raw field -> feature name(s) so ablation on a raw field can describe itself.
_RAW_TO_FEATURE = {
    "temp_max_c": "temp_max_c",
    "temp_min_c": "temp_min_c",
    "relative_humidity_pct": "relative_humidity_pct",
    "wind_max_kmh": "wind_max_kmh",
    "precip_total_mm": "precip_total_mm",
    "precip_intensity_max_mmh": "precip_intensity_max_mmh",
    "visibility_km": "visibility_km",
    "lightning_min_distance_km": "lightning_min_distance_km",
    "rain_prev_72h_mm": "rain_prev_72h_mm",
    "soil_moisture_pct": "soil_moisture_pct",
    "river_stage_above_normal_m": "river_stage_above_normal_m",
    "distance_to_river_m": "distance_to_river_km",
    "elevation_above_river_m": "elevation_above_river_m",
    "wildlife_sightings_24h": "wildlife_sightings_24h",
    "wildlife_sightings_7d": "wildlife_sightings_7d",
    "wildlife_max_threat_level": "wildlife_max_threat_level",
}

_FEATURE_CATEGORY = {name: cat for name, _, _, cat in FEATURE_SPEC}


def describe_field(raw_field, value):
    """Human-readable description of a raw field's current value."""
    feature = _RAW_TO_FEATURE.get(raw_field, raw_field)
    template = _DESCRIPTIONS.get(feature, f"{raw_field} = {{v:.2f}}")
    if isinstance(value, bool) or (isinstance(value, float) and math.isnan(value)):
        text = template.split(" {v")[0] if "{v" in template else template
        if isinstance(value, float) and math.isnan(value):
            return f"{text} (not reported)"
        return text
    try:
        return template.format(v=float(value))
    except (TypeError, ValueError):
        return f"{raw_field} = {value}"


def feature_category(name):
    """Category for a feature or raw field name (display grouping)."""
    if name in _FEATURE_CATEGORY:
        return _FEATURE_CATEGORY[name]
    feature = _RAW_TO_FEATURE.get(name)
    return _FEATURE_CATEGORY.get(feature, "other")

"""ML hazard model: the chance that NOAA logs a damaging storm, flood, heat, wind or fire
event near a site on a given day, estimated from that day's weather.

ml/fit_hazard_model.py fits it (logistic regression) on NOAA Storm Events reports and
historical daily weather at the 58 sites, and writes the coefficients to
ml/hazard_model.json. Without that file the app scores with the rules in hazards.py alone.
"""
import json
import math
from datetime import date
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[2] / "ml" / "hazard_model.json"

# Inputs for one site-day, built from the daily weather that weather.summarize() keeps.
FEATURES = [
    "heat_index_max_f",   # daily max apparent temperature
    "heat_above_90_f",    # degrees above 90 °F, where the NWS "extreme caution" band starts
    "rain_log",           # log(1 + rain in inches)
    "rain_hours",
    "rain_prev_3d_log",   # log(1 + rain over the 3 days before): wet ground, rising water
    "gust_max_mph",
    "gust_above_30_mph",  # gusts beyond common crane and aerial-lift limits
    "wind_max_mph",
    "humidity_min_pct",
    "season_sin",         # time of year
    "season_cos",
    "lat",                # region
    "lng",
]
# The hazard each input speaks to, for the "main factor" in explanations.
FACTOR = {
    "heat_index_max_f": "heat", "heat_above_90_f": "heat",
    "rain_log": "flooding", "rain_hours": "flooding", "rain_prev_3d_log": "flooding",
    "gust_max_mph": "wind", "gust_above_30_mph": "wind", "wind_max_mph": "wind",
}
REQUIRED = ("date", "heatIndexMaxF", "precipIn", "precipHours", "gustMaxMph", "windMaxMph", "humidityMinPct")


def load(path=MODEL_PATH):
    """The fitted model, or None if it hasn't been fitted (or doesn't match FEATURES)."""
    try:
        model = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return model if model.get("features") == FEATURES else None


MODEL = load()


def day_features(day, previous_days, lat, lng):
    """Model inputs for one site-day, or None when a reading is missing.

    day, previous_days: daily weather dicts with weather.summarize()'s keys (previous_days
    are the up-to-3 days before `day`, used for recent rain).
    """
    if lat is None or lng is None or any(day.get(key) is None for key in REQUIRED):
        return None
    heat, gust = day["heatIndexMaxF"], day["gustMaxMph"]
    rain_before = sum(d.get("precipIn") or 0 for d in previous_days)
    angle = 2 * math.pi * date.fromisoformat(day["date"]).timetuple().tm_yday / 365.25
    return [
        heat, max(0.0, heat - 90),
        math.log1p(max(day["precipIn"], 0)), day["precipHours"], math.log1p(max(rain_before, 0)),
        gust, max(0.0, gust - 30), day["windMaxMph"],
        day["humidityMinPct"],
        math.sin(angle), math.cos(angle),
        lat, lng,
    ]


def predict(features, model=None):
    """(probability 0-1, main hazard factor or None) for one site-day, or None without a model or inputs."""
    model = model or MODEL
    if model is None or features is None:
        return None
    pushes = [c * (x - m) / s for c, x, m, s in zip(model["coef"], features, model["mean"], model["scale"])]
    z = model["intercept"] + sum(pushes)
    probability = 1 / (1 + math.exp(-max(-40.0, min(40.0, z))))
    # The hazard whose inputs push the risk up the most (season and region are left out).
    by_factor = {}
    for name, push in zip(FEATURES, pushes):
        if name in FACTOR:
            by_factor[FACTOR[name]] = by_factor.get(FACTOR[name], 0.0) + push
    factor = max(by_factor, key=by_factor.get)
    return probability, factor if by_factor[factor] > 0 else None

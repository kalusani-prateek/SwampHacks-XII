"""ML hazard model: inputs, predictions, how it combines with the safety rules, and the fitting helpers."""
import csv
import gzip
import math
from datetime import datetime

import numpy as np
import pytest

from app.services import hazard_model
from app.services.hazards import score_site
from ml.fit_hazard_model import event_days, fit_logistic, hazardous_days, probabilities, roc_auc

RULES = {"lightningRadiusMiles": 10, "lightningAllClearMinutes": 30, "floodRainInches": 2,
         "heatIndexF": 105, "windMph": 35, "hazardIndexAlert": 7.5}
NOW = datetime(2026, 7, 15, 16, 0)
SITE = {"waterway": None, "lat": 25.4356, "lng": -80.3308}

# A hand-made model where only heat matters: risk rises 0.3 log-odds per °F above 90.
HEAT_ONLY = {"features": hazard_model.FEATURES, "intercept": -3.0,
             "mean": [0.0] * len(hazard_model.FEATURES), "scale": [1.0] * len(hazard_model.FEATURES),
             "coef": [0.3 if name == "heat_above_90_f" else 0.0 for name in hazard_model.FEATURES]}


def day(date="2026-07-15", heat=88, rain=0.0, gust=12):
    return {"date": date, "heatIndexMaxF": heat, "precipIn": rain, "precipHours": 2 if rain else 0,
            "gustMaxMph": gust, "windMaxMph": gust / 2, "humidityMinPct": 55}


def week(today_heat, tomorrow_heat=88):
    """Three past days, today and tomorrow, as weather.summarize() lays them out."""
    days = [day(f"2026-07-{d}") for d in (12, 13, 14)] + [day("2026-07-15", today_heat), day("2026-07-16", tomorrow_heat)]
    return {"daily": days, "todayIndex": 3}


@pytest.fixture
def heat_model(monkeypatch):
    monkeypatch.setattr(hazard_model, "MODEL", HEAT_ONLY)


def test_inputs_need_complete_weather_and_a_location():
    features = hazard_model.day_features(day(heat=95), [day(rain=1.0), day(rain=0.5)], 25.4, -80.3)
    assert len(features) == len(hazard_model.FEATURES)
    named = dict(zip(hazard_model.FEATURES, features))
    assert named["heat_above_90_f"] == 5 and named["rain_prev_3d_log"] == pytest.approx(math.log1p(1.5))
    assert hazard_model.day_features({**day(), "gustMaxMph": None}, [], 25.4, -80.3) is None
    assert hazard_model.day_features(day(), [], None, None) is None


def test_prediction_and_main_factor():
    hot = hazard_model.predict(hazard_model.day_features(day(heat=110), [], 25.4, -80.3), HEAT_ONLY)
    mild = hazard_model.predict(hazard_model.day_features(day(heat=85), [], 25.4, -80.3), HEAT_ONLY)
    assert hot[0] == pytest.approx(1 / (1 + math.exp(-3))) and hot[1] == "heat"
    assert mild[0] < 0.05 and mild[1] is None  # nothing pushing the risk up
    assert hazard_model.predict(None, HEAT_ONLY) is None


def test_model_raises_the_index_and_says_why(heat_model):
    scored = score_site({**SITE, "weather": week(today_heat=110)}, [], 0, RULES, NOW)
    assert scored["hazardIndex"] == 9.5  # 10 x 95% chance
    assert scored["conditions"]["modelRiskPct"] == 95
    assert any(d.startswith("Hazard model: 95% chance") and d.endswith("mainly extreme heat") for d in scored["drivers"])


def test_safety_rules_still_win_when_they_are_higher(heat_model):
    weather = week(today_heat=85)
    scored = score_site({**SITE, "weather": weather, "nws": {"alerts": [{"event": "Tornado Warning"}]}}, [], 0, RULES, NOW)
    assert scored["hazardIndex"] == 10
    assert not any(d.startswith("Hazard model") for d in scored["drivers"])


def test_forecast_days_are_scored_by_the_model_too(heat_model):
    forecast = score_site({**SITE, "weather": week(today_heat=85, tomorrow_heat=110)}, [], 0, RULES, NOW)["forecast"]
    assert forecast[0]["date"] == "2026-07-16" and forecast[0]["hazardIndex"] == 9.5 and forecast[0]["topHazard"] == "heat"


def test_without_a_fitted_model_scoring_is_rules_only(monkeypatch):
    monkeypatch.setattr(hazard_model, "MODEL", None)
    scored = score_site({**SITE, "weather": week(today_heat=110)}, [], 0, RULES, NOW)
    assert "modelRiskPct" not in scored["conditions"]
    assert not any(d.startswith("Hazard model") for d in scored["drivers"])


# --- Fitting helpers (ml/fit_hazard_model.py) ----------------------------------

def test_roc_auc_counts_ties_as_half():
    assert roc_auc([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]) == 0.75
    assert roc_auc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]) == 0.5


def test_logistic_fit_learns_a_clear_signal():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(2000, 2))
    y = (X[:, 0] + 0.3 * rng.normal(size=2000) > 1).astype(float)  # only the first input matters
    model = fit_logistic(X, y)
    assert model["coef"][0] > 2 * abs(model["coef"][1])
    assert roc_auc(y, probabilities(model, X)) > 0.95


def test_event_days_cover_the_span_but_cap_long_events():
    row = {"BEGIN_YEARMONTH": "202507", "BEGIN_DAY": "30", "END_YEARMONTH": "202508", "END_DAY": "1"}
    assert event_days(row) == ["2025-07-30", "2025-07-31", "2025-08-01"]
    assert len(event_days({**row, "END_DAY": "28"})) == 10


def test_reports_are_matched_by_distance_or_by_zone(tmp_path):
    columns = ["BEGIN_YEARMONTH", "BEGIN_DAY", "END_YEARMONTH", "END_DAY", "STATE_FIPS", "EVENT_TYPE",
               "CZ_TYPE", "CZ_FIPS", "BEGIN_LAT", "BEGIN_LON", "END_LAT", "END_LON"]
    rows = [
        ["202507", "4", "202507", "4", "12", "Lightning", "C", "86", "25.58", "-80.33", "", ""],       # ~10 mi: counts
        ["202507", "5", "202507", "5", "12", "Hail", "C", "86", "26.0", "-80.33", "", ""],             # ~39 mi: too far
        ["202507", "10", "202507", "11", "12", "Excessive Heat", "Z", "173", "", "", "", ""],          # the site's zone
        ["202507", "12", "202507", "12", "12", "Excessive Heat", "Z", "174", "", "", "", ""],          # another zone
        ["202501", "20", "202501", "20", "12", "Winter Storm", "Z", "173", "", "", "", ""],            # not a crew hazard here
    ]
    path = tmp_path / "storm_details_2025.csv.gz"
    with gzip.open(path, "wt", newline="") as f:
        csv.writer(f).writerows([columns, *rows])
    days = hazardous_days([path], [{"id": "turkey-point", **SITE}], {"turkey-point": ["FLZ173", "FLC086"]})
    assert days == {("turkey-point", "2025-07-04"), ("turkey-point", "2025-07-10"), ("turkey-point", "2025-07-11")}

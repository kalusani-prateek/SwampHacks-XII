"""Acceptance tests + demo for the hazard model.

Run (from backend/):
    ../venv/bin/python -m ml.selftest

Rules tests always run. Model tests need the trained artifact
(artifacts/hazard_model.joblib, produced by `python -m ml.train`) and are
skipped with a note if it is missing. Exit code 0 = everything passed.
"""

import math
from pathlib import Path

import backend.ml.model as model
from ml import rules, synthetic
from ml.schema import FEATURE_NAMES, RAW_FIELDS, build_feature_matrix, normalize

ARTIFACT = Path(__file__).resolve().parent.parent / "artifacts" / "hazard_model.joblib"


def safe_site(**overrides):
    row = {"site_id": "T", "temp_max_c": 22.0, "temp_min_c": 15.0,
           "relative_humidity_pct": 50.0, "wind_max_kmh": 8.0, "precip_total_mm": 0.0,
           "precip_intensity_max_mmh": 0.0, "severe_weather_flag": False,
           "visibility_km": 15.0, "lightning_min_distance_km": 90.0,
           "minutes_since_last_strike_min": None, "rain_prev_72h_mm": 0.0,
           "soil_moisture_pct": 45.0, "river_stage_above_normal_m": 0.2,
           "distance_to_river_m": 25000.0, "elevation_above_river_m": 10.0,
           "is_wetland": False, "wildlife_sightings_24h": 0,
           "wildlife_sightings_7d": 0, "wildlife_max_threat_level": 0.0}
    row.update(overrides)
    return row


# ---------------------------------------------------------------- rules only

def test_safe_site_scores_low():
    report = model.predict_site(safe_site())
    assert report["hazard_index"] < 2.5, report
    assert report["band"] == "low", report


def test_lightning_rule():
    # Strike within 10 miles, minutes known and inside the window
    report = model.predict_site(safe_site(lightning_min_distance_km=8,
                                          minutes_since_last_strike_min=10))
    assert report["hazard_index"] >= 8.0, report
    assert report["work_restricted"] is True, report
    assert "30" in report["restriction_reason"], report

    # Same strike, window expired: still dangerous, no restriction
    expired = model.predict_site(safe_site(lightning_min_distance_km=8,
                                           minutes_since_last_strike_min=45))
    assert expired["hazard_index"] >= 8.0, expired
    assert expired["work_restricted"] is False, expired

    # Strike beyond 10 miles: no restriction
    far = model.predict_site(safe_site(lightning_min_distance_km=20,
                                       minutes_since_last_strike_min=5))
    assert far["work_restricted"] is False, far


def test_heat_scores_high():
    report = model.predict_site(safe_site(temp_max_c=41, relative_humidity_pct=70))
    assert report["hazard_index"] >= 7.0, report
    assert report["band"] in ("high", "critical"), report
    assert report["sub_scores"]["heat"] > 8.0, report


def test_flood_interaction():
    # Soil is held equal (80%) so FLOOD is the dominant category and the
    # near-river vs far-river gap is actually visible in the index.
    near = model.predict_site(safe_site(precip_total_mm=120, rain_prev_72h_mm=150,
                                       river_stage_above_normal_m=2.5,
                                       distance_to_river_m=500,
                                       elevation_above_river_m=0.5,
                                       soil_moisture_pct=80))
    far = model.predict_site(safe_site(precip_total_mm=120, rain_prev_72h_mm=150,
                                       river_stage_above_normal_m=2.5,
                                       distance_to_river_m=10000,
                                       soil_moisture_pct=80))
    assert near["hazard_index"] >= 5.5, near
    assert near["hazard_index"] > far["hazard_index"] + 2.0, (near, far)


def test_wildlife_scoring():
    single = model.predict_site(safe_site(wildlife_sightings_24h=1,
                                         wildlife_sightings_7d=1,
                                         wildlife_max_threat_level=5))
    sustained = model.predict_site(safe_site(wildlife_sightings_24h=5,
                                             wildlife_sightings_7d=25,
                                             wildlife_max_threat_level=5))
    assert 2.5 <= single["sub_scores"]["wildlife"] <= 4.0, single
    assert sustained["sub_scores"]["wildlife"] > 9.0, sustained


def test_band_edges():
    for index, expected in [(0.0, "low"), (2.49, "low"), (2.5, "moderate"),
                           (4.99, "moderate"), (5.0, "high"), (7.49, "high"),
                           (7.5, "critical"), (10.0, "critical")]:
        assert rules.band(index) == expected, (index, rules.band(index))


def test_normalize_is_bombproof():
    bad = {"site_id": 123, "temp_max_c": "hot", "wind_max_kmh": 1e9,
           "severe_weather_flag": "YES", "distance_to_river_m": -5,
           "surprise": None}
    c = normalize(bad)
    assert c["site_id"] == "123"
    assert math.isnan(c["temp_max_c"])
    assert c["wind_max_kmh"] == 250.0          # clamped
    assert c["distance_to_river_m"] == 0.0     # clamped
    assert c["severe_weather_flag"] is True
    assert len(c["_issues"]) >= 3
    report = model.predict_site(bad)
    assert 0 <= report["hazard_index"] <= 10


# ------------------------------------------------------------ model required

def _load_bundle():
    if not ARTIFACT.exists():
        return None
    import joblib
    return joblib.load(ARTIFACT)


def test_dry_lightning_raw_prediction(bundle):
    """Calm conditions + close strike: the model itself (not the floor
    override) must score high — guards against generator blind spots."""
    canonical = normalize(safe_site(lightning_min_distance_km=6,
                                    minutes_since_last_strike_min=3))
    raw = float(bundle["model"].predict(build_feature_matrix([canonical]))[0])
    assert raw >= 7.0, raw


def test_output_range_on_synthetic(bundle):
    train_df, _ = synthetic.make_dataset(n_train_sites=10, n_eval_sites=3,
                                          days=20, seed=7)
    for row in train_df.sample(150, random_state=1).to_dict("records"):
        report = model.predict_site(row)
        assert 0 <= report["hazard_index"] <= 10, report
    worst = model.predict_site(safe_site(
        temp_max_c=48, relative_humidity_pct=95, wind_max_kmh=140,
        precip_total_mm=400, precip_intensity_max_mmh=120, severe_weather_flag=True,
        visibility_km=0.2, lightning_min_distance_km=2, rain_prev_72h_mm=500,
        soil_moisture_pct=100, river_stage_above_normal_m=5.0,
        distance_to_river_m=50, elevation_above_river_m=0.5, is_wetland=True,
        wildlife_sightings_24h=20, wildlife_sightings_7d=60,
        wildlife_max_threat_level=5))
    assert 0 <= worst["hazard_index"] <= 10, worst
    assert worst["band"] == "critical", worst


def test_missing_field_robustness(bundle):
    base = safe_site(precip_total_mm=90, distance_to_river_m=600,
                     soil_moisture_pct=85, lightning_min_distance_km=35)
    for field in [k for k in RAW_FIELDS if k not in ("site_id",)]:
        row = {k: v for k, v in base.items() if k != field}
        report = model.predict_site(row)
        assert 0 <= report["hazard_index"] <= 10, (field, report)
    everything_gone = {"site_id": "ghost"}
    report = model.predict_site(everything_gone)
    assert 0 <= report["hazard_index"] <= 10, report
    assert report["data_completeness"] == 0.0, report


def test_monotonicity(bundle):
    """More rain/heat/wind/moisture, closer lightning/rivers -> the index
    must never drop. Guaranteed by monotonic constraints; also catches any
    feature-order scrambling between training and inference."""
    sweeps = [
        ("temp_max_c", [10, 20, 30, 35, 40, 45]),
        ("wind_max_kmh", [0, 20, 50, 80, 110]),
        ("precip_total_mm", [0, 20, 50, 100, 200]),
        ("soil_moisture_pct", [10, 30, 50, 70, 90, 100]),
        ("rain_prev_72h_mm", [0, 50, 100, 200, 300]),
        ("river_stage_above_normal_m", [0, 0.5, 1.5, 3, 5]),
        ("lightning_min_distance_km", [90, 60, 40, 25, 16, 10, 5]),
        ("distance_to_river_m", [40000, 20000, 8000, 2000, 500, 100]),
        ("visibility_km", [20, 10, 5, 1]),
        ("wildlife_max_threat_level", [0, 1, 2.5, 4, 5]),
        ("severe_weather_flag", [False, True]),
    ]
    for field, values in sweeps:
        rows = [normalize(safe_site(**{field: v})) for v in values]
        preds = bundle["model"].predict(build_feature_matrix(rows))
        for i in range(1, len(preds)):
            assert preds[i] >= preds[i - 1] - 1e-9, \
                f"monotonicity violated for {field}: {list(zip(values, preds))}"


def test_ranked_scenarios(bundle):
    scenarios = {
        "BOLT": safe_site(site_id="BOLT", lightning_min_distance_km=6, minutes_since_last_strike_min=3),
        "HEAT": safe_site(site_id="HEAT", temp_max_c=41, relative_humidity_pct=70),
        "FLOOD": safe_site(site_id="FLOOD", precip_total_mm=120, rain_prev_72h_mm=150,
                           river_stage_above_normal_m=2.5, distance_to_river_m=500,
                           elevation_above_river_m=0.5, soil_moisture_pct=80,
                           wind_max_kmh=30),
        "GATOR": safe_site(site_id="GATOR", wildlife_sightings_24h=1, wildlife_sightings_7d=1,
                           wildlife_max_threat_level=5),
        "SAFE": safe_site(site_id="SAFE"),
    }
    ranked = model.rank_sites(list(scenarios.values()))
    order = [r["site_id"] for r in ranked]
    expected = ["BOLT", "HEAT", "FLOOD", "GATOR", "SAFE"]
    assert order == expected, (order, expected)
    assert ranked[0]["work_restricted"] is True


def test_artifact_contract(bundle):
    assert list(bundle["feature_names"]) == list(FEATURE_NAMES)
    assert len(bundle["monotonic_cst"]) == len(FEATURE_NAMES)
    assert bundle["metrics"]["oof"]["mae"] < 0.75, bundle["metrics"]
    if "eval" in bundle["metrics"]:
        assert bundle["metrics"]["eval"]["spearman"] > 0.90, bundle["metrics"]
    assert bundle["band_edges"] == [2.5, 5.0, 7.5]
    assert len(bundle["categories"]) == 6


def test_rules_fallback(bundle):
    saved_path, saved_bundle = model.ARTIFACT_PATH, model._BUNDLE
    try:
        model.ARTIFACT_PATH = Path("/nonexistent/hazard_model.joblib")
        model._BUNDLE = None
        report = model.predict_site(safe_site(temp_max_c=38))
        assert report["model_version"] == "rules_fallback", report
        assert 0 <= report["hazard_index"] <= 10
    finally:
        model.ARTIFACT_PATH = saved_path
        model._BUNDLE = saved_bundle


# ------------------------------------------------------------------- demo

def demo_ranking():
    scenarios = [
        ("Wetland substation", safe_site(
            site_id="wetland-substation", temp_max_c=36, relative_humidity_pct=75,
            precip_total_mm=95, rain_prev_72h_mm=140, river_stage_above_normal_m=2.1,
            distance_to_river_m=420, elevation_above_river_m=1.2, soil_moisture_pct=93,
            is_wetland=True, wildlife_sightings_24h=3, wildlife_sightings_7d=9,
            wildlife_max_threat_level=5, lightning_min_distance_km=22,
            severe_weather_flag=True, wind_max_kmh=55)),
        ("Riverside pump house", safe_site(
            site_id="riverside-pump", temp_max_c=31, precip_total_mm=70,
            rain_prev_72h_mm=110, river_stage_above_normal_m=1.6, distance_to_river_m=900,
            soil_moisture_pct=88, lightning_min_distance_km=45, wind_max_kmh=40)),
        ("Forest clearing", safe_site(
            site_id="forest-clearing", temp_max_c=39, relative_humidity_pct=60,
            lightning_min_distance_km=12, minutes_since_last_strike_min=8,
            wind_max_kmh=25, wildlife_sightings_24h=2, wildlife_sightings_7d=5,
            wildlife_max_threat_level=4)),
        ("Urban depot", safe_site(
            site_id="urban-depot", temp_max_c=29, wind_max_kmh=12,
            wildlife_sightings_24h=1, wildlife_sightings_7d=2,
            wildlife_max_threat_level=2)),
    ]
    ranked = model.rank_sites([s[1] for s in scenarios])
    print("\ndemo — 6PM next-day ranking (what the admin dashboard shows)")
    print(f"{'rank':<5}{'site':<22}{'index':<7}{'band':<10}{'restricted':<11}top factor")
    for report in ranked:
        top = report["top_factors"][0] if report["top_factors"] else None
        top_text = f"{top['description']} ({top['direction']} {abs(top['delta'])})" if top else "-"
        print(f"{report['rank']:<5}{report['site_id']:<22}{report['hazard_index']:<7}"
              f"{report['band']:<10}{str(report['work_restricted']):<11}{top_text}")


def main():
    bundle = _load_bundle()
    if bundle is None:
        print("[skip] no artifact at", ARTIFACT, "— run `python -m ml.train` first")

    tests = [
        ("safe site scores low", lambda: test_safe_site_scores_low()),
        ("lightning 10-mile rule", lambda: test_lightning_rule()),
        ("extreme heat scores high", lambda: test_heat_scores_high()),
        ("flood interaction (near vs far river)", lambda: test_flood_interaction()),
        ("wildlife scoring", lambda: test_wildlife_scoring()),
        ("band thresholds", lambda: test_band_edges()),
        ("normalize bombproof", lambda: test_normalize_is_bombproof()),
        ("dry-lightning raw prediction", lambda: test_dry_lightning_raw_prediction(bundle)),
        ("output range on synthetic + extremes", lambda: test_output_range_on_synthetic(bundle)),
        ("missing-field robustness", lambda: test_missing_field_robustness(bundle)),
        ("monotonicity sweeps", lambda: test_monotonicity(bundle)),
        ("crafted scenario ranking", lambda: test_ranked_scenarios(bundle)),
        ("artifact contract", lambda: test_artifact_contract(bundle)),
        ("rules fallback mode", lambda: test_rules_fallback(bundle)),
    ]

    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {name}: {e}")
        except TypeError as e:
            # bundle is None -> model test on missing artifact
            print(f"SKIP  {name}: {e}")

    if bundle is not None and failures == 0:
        demo_ranking()
        print("\nall tests passed")
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if main() else 0)

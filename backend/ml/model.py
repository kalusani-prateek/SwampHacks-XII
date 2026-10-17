"""Runtime hazard-index interface — what the Flask app imports.

    import model
    report = model.predict_site(raw_conditions_dict)   # one site
    ranked = model.rank_sites([raw_dict, ...])         # all 50 sites, sorted

Never touches Flask, SQLAlchemy or the network: it loads the joblib artifact
trained by `ml.train` and scores whatever dict it is given. If the artifact
is missing or unreadable it falls back to the expert rules (marked
`rules_fallback`) so a demo never dies mid-pitch.
"""

import warnings
import sys
from pathlib import Path

try:  # imported as part of the `backend` package
    from . import rules
    from .schema import (FEATURE_NAMES, LIGHTNING_NO_WORK_KM, SAFE_BASELINE, build_feature_matrix,
                            describe_field, feature_category, normalize)
except ImportError:  # run from backend/ (python run.py, python -m ml.train)
    from ml import rules
    from ml.schema import (FEATURE_NAMES, LIGHTNING_NO_WORK_KM, SAFE_BASELINE, build_feature_matrix,
                           describe_field, feature_category, normalize)

ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "hazard_model.joblib"

# A strike within 10 miles is a hard operational rule — the index can never
# read below this while the no-work rule is active, whatever the model says.
RESTRICTION_INDEX_FLOOR = 8.0

_BUNDLE = None


def load_model(force=False):
    """Load (and cache) the trained artifact; returns the bundle dict."""
    global _BUNDLE
    print(f"[DEBUG] load_model: ARTIFACT_PATH={ARTIFACT_PATH}", file=sys.stderr)
    if _BUNDLE is not None and not force:
        return _BUNDLE
    if not ARTIFACT_PATH.exists():
        warnings.warn(f"hazard model artifact not found at {ARTIFACT_PATH}; "
                      "scoring falls back to expert rules (run ml.train)")
        return None
    import joblib

    bundle = joblib.load(ARTIFACT_PATH)
    if list(bundle["feature_names"]) != list(FEATURE_NAMES):
        raise RuntimeError("model artifact was trained against a different "
                           "feature schema — retrain with `python -m ml.train`")
    _BUNDLE = bundle
    return bundle


def _clip01(x):
    return max(0.0, min(10.0, float(x)))


def _completeness(canonical):
    """Share of scoreable fields actually provided (0-1) — a confidence
    signal for the UI when the API payload is sparse."""
    import math

    fields = list(SAFE_BASELINE)
    present = 0
    for field in fields:
        v = canonical.get(field)
        if v is None:
            continue
        if isinstance(v, float) and math.isnan(v):
            continue
        present += 1
    return round(present / len(fields), 2)


def _top_factors(model, canonical, base_index, k=5):
    """Counterfactual explanations: reset each raw field to a safe baseline,
    re-predict, and report how much the index moved. No SHAP dependency."""
    fields = list(SAFE_BASELINE)
    counter_rows = []
    for field in fields:
        cf = dict(canonical)
        cf[field] = SAFE_BASELINE[field]
        counter_rows.append(cf)
    preds = model.predict(build_feature_matrix(counter_rows))

    factors = []
    for field, pred in zip(fields, preds):
        delta = base_index - _clip01(pred)
        if abs(delta) < 0.05:
            continue
        value = canonical.get(field)
        factors.append({
            "field": field,
            "category": feature_category(field),
            "value": value if value is not None else None,
            "description": describe_field(field, value),
            "delta": round(delta, 2),
            "direction": "raises" if delta > 0 else "lowers",
        })
    factors.sort(key=lambda f: -abs(f["delta"]))
    return factors[:k]


def predict_site(raw):
    """Raw condition dict -> full hazard report (see MODEL.md for the schema)."""
    canonical = normalize(raw)
    expert = rules.score_site(canonical)
    bundle = load_model()

    if bundle is None:
        return {
            "site_id": canonical["site_id"],
            "forecast_date": canonical["forecast_date"] or None,
            "hazard_index": expert["index"],
            "band": expert["band"],
            "sub_scores": expert["sub_scores"],
            "top_factors": [],
            "work_restricted": expert["work_restricted"],
            "restriction_reason": expert["restriction_reason"],
            "model_version": "rules_fallback",
            "data_completeness": _completeness(canonical),
            "input_issues": canonical["_issues"],
        }

    model = bundle["model"]
    pred = _clip01(model.predict(build_feature_matrix([canonical]))[0])

    # Hard safety override: a strike within 10 miles always raises the index
    # to at least 8.0, regardless of when it occurred (minutes_since_last_strike_min
    # only gates the work_restricted flag, not the index hazard).
    d = rules._num(canonical, "lightning_min_distance_km")
    if d is not None and d <= LIGHTNING_NO_WORK_KM:
        pred = max(pred, RESTRICTION_INDEX_FLOOR)

    return {
        "site_id": canonical["site_id"],
        "forecast_date": canonical["forecast_date"] or None,
        "hazard_index": round(pred, 2),
        "band": rules.band(pred),
        "sub_scores": expert["sub_scores"],
        "top_factors": _top_factors(model, canonical, pred),
        "work_restricted": expert["work_restricted"],
        "restriction_reason": expert["restriction_reason"],
        "model_version": bundle["model_version"],
        "data_completeness": _completeness(canonical),
        "input_issues": canonical["_issues"],
    }


def rank_sites(raw_rows):
    """Score a batch of sites and sort by hazard (most dangerous first)."""
    reports = [predict_site(raw) for raw in raw_rows]
    reports.sort(key=lambda r: -r["hazard_index"])
    for rank, report in enumerate(reports, start=1):
        report["rank"] = rank
    return reports


def healthcheck():
    """Status dict for a future /api/health route."""
    bundle = load_model()
    if bundle is None:
        return {"status": "degraded", "artifact": str(ARTIFACT_PATH),
                "mode": "rules_fallback"}
    return {
        "status": "ok",
        "artifact": str(ARTIFACT_PATH),
        "model_version": bundle["model_version"],
        "schema_version": bundle["schema_version"],
        "sklearn_version": bundle["sklearn_version"],
        "trained_at": bundle["trained_at"],
        "metrics": bundle["metrics"],
    }
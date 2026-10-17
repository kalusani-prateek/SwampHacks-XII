"""Train the hazard-index model.

Usage (from backend/):
    ../venv/bin/python -m ml.train [--sites 220] [--eval-sites 40] [--days 60]
        [--folds 5] [--seed 42] [--sigma 0.35]
        [--labels data.csv] [--out artifacts/hazard_model.joblib]

Protocol (anti-overfitting by construction):
  * trains on synthetic site-days, never the 50 real sample locations
  * GroupKFold by site id -> honest generalization-to-unseen-sites estimate
  * monotonic constraints encode known-safe directions (more rain never
    lowers hazard), shrinking the hypothesis space
  * fixed hyperparameters + early stopping; no tuning on synthetic data
    (tuning against fake labels is its own overfitting)
  * final refit on all rows with the median early-stopped iteration count
  * label noise sigma sets the MAE floor (sigma * sqrt(2/pi) ~ 0.28):
    OOF MAE near that floor means the rule surface is fully learned

With --labels, retrains on real data instead (canonical columns + site_id +
hazard_label), which is the path once real incident scores accumulate.
"""

import argparse
import inspect
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold

from ml import MODEL_VERSION, SCHEMA_VERSION
from ml import rules, synthetic
from ml.schema import (BAND_EDGES, CATEGORIES, FEATURE_NAMES, MONOTONIC_CST,
                       build_feature_matrix)

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT = BACKEND_DIR / "artifacts" / "hazard_model.joblib"

# Fixed, defensible hyperparameters — deliberately NOT tuned.
# Further reduced L2 regularization to allow stronger feature weights for flood/exposure features
PARAMS = dict(loss="squared_error", learning_rate=0.05, max_leaf_nodes=63,
              min_samples_leaf=25, l2_regularization=0.01, max_bins=255,
              random_state=123, monotonic_cst=MONOTONIC_CST)


def _metrics(y_true, y_pred):
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(math.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
        "spearman": float(spearmanr(y_true, y_pred).statistic),
    }


def make_estimator(max_iter, early_stopping):
    params = dict(PARAMS)
    params["max_iter"] = int(max_iter)
    params["early_stopping"] = early_stopping
    if early_stopping:
        params["validation_fraction"] = 0.15
        params["n_iter_no_change"] = 25
        params["tol"] = 1e-7
    return HistGradientBoostingRegressor(**params)


def load_training_data(args):
    """Returns (train_df, eval_df or None). Both need canonical columns."""
    if args.labels:
        path = Path(args.labels)
        if not path.exists():
            sys.exit(f"error: labels file not found: {path}")
        df = pd.read_csv(path)
        if "site_id" not in df.columns or "hazard_label" not in df.columns:
            sys.exit("error: labels CSV needs `site_id` and `hazard_label` columns "
                     "plus canonical condition columns (see ml/schema.py RAW_FIELDS)")
        print(f"[data] real labeled data: {len(df)} rows from {path}")
        return df, None

    print(f"[data] generating {args.sites}x{args.days} train + "
          f"{args.eval_sites}x{args.days} eval synthetic site-days "
          f"(seed={args.seed}, sigma={args.sigma})")
    train_df, eval_df = synthetic.make_dataset(
        n_train_sites=args.sites, n_eval_sites=args.eval_sites,
        days=args.days, seed=args.seed, sigma=args.sigma)
    print(f"[data] train rows: {len(train_df)} | eval rows (unseen sites): {len(eval_df)}")
    return train_df, eval_df


def run_cv(train_df, folds):
    """GroupKFold-by-site CV; returns (oof_metrics, fold_metrics, n_iters, oof)."""
    rows = train_df.to_dict("records")
    X = build_feature_matrix(rows)
    y = train_df["hazard_label"].to_numpy()
    groups = train_df["site_id"].to_numpy()

    gkf = GroupKFold(n_splits=folds)
    oof = np.full(len(y), np.nan)
    fold_metrics, n_iters = [], []
    for i, (tr, te) in enumerate(gkf.split(X, y, groups)):
        est = make_estimator(max_iter=600, early_stopping=True)
        est.fit(X.iloc[tr], y[tr])
        oof[te] = est.predict(X.iloc[te])
        fold_metrics.append(_metrics(y[te], oof[te]))
        n_iters.append(int(est.n_iter_))
        print(f"[cv] fold {i + 1}/{folds}: MAE={fold_metrics[-1]['mae']:.3f} "
              f"R2={fold_metrics[-1]['r2']:.3f} iters={n_iters[-1]}")

    assert not np.isnan(oof).any(), "OOF predictions incomplete"
    oof_metrics = _metrics(y, oof)
    oof_metrics["rules_mae"] = float(mean_absolute_error(
        y, [rules.score_site(r)["index"] for r in rows]))
    return oof_metrics, fold_metrics, n_iters, oof


def evaluate_on(model, eval_df):
    """Model vs noise-free expert labels on held-out sites (true-surface error)."""
    rows = eval_df.to_dict("records")
    X = build_feature_matrix(rows)
    y = eval_df["hazard_label"].to_numpy()
    pred = np.clip(model.predict(X), 0.0, 10.0)
    m = _metrics(y, pred)
    m["constant5_mae"] = float(mean_absolute_error(y, np.full(len(y), 5.0)))
    m["model_vs_rules_mae"] = float(mean_absolute_error(
        pred, [rules.score_site(r)["index"] for r in rows]))
    return m


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sites", type=int, default=220)
    parser.add_argument("--eval-sites", type=int, default=40)
    parser.add_argument("--days", type=int, default=60)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sigma", type=float, default=synthetic.LABEL_SIGMA)
    parser.add_argument("--labels", type=str, default=None,
                        help="CSV with canonical columns + site_id + hazard_label")
    parser.add_argument("--out", type=str, default=str(DEFAULT_OUT))
    args = parser.parse_args()

    if "monotonic_cst" not in inspect.signature(
            HistGradientBoostingRegressor.__init__).parameters:
        sys.exit("error: this sklearn version lacks monotonic_cst on "
                 "HistGradientBoostingRegressor; install scikit-learn>=1.3")

    train_df, eval_df = load_training_data(args)
    oof_metrics, fold_metrics, n_iters, _ = run_cv(train_df, args.folds)

    # Final refit: all rows, deterministic iteration budget from CV.
    final_iter = math.ceil(1.15 * np.median(n_iters))
    all_rows = train_df.to_dict("records")
    X_all = build_feature_matrix(all_rows)
    y_all = train_df["hazard_label"].to_numpy()
    print(f"[fit] final model on all {len(y_all)} rows, max_iter={final_iter}")
    final_model = make_estimator(max_iter=final_iter, early_stopping=False)
    final_model.fit(X_all, y_all)

    metrics = {"oof": oof_metrics, "fold_n_iter": n_iters, "final_iter": final_iter}
    if eval_df is not None:
        metrics["eval"] = evaluate_on(final_model, eval_df)

    noise_floor = args.sigma * math.sqrt(2 / math.pi)
    print("\n=== metrics ===")
    print(f"OOF (GroupKFold-{args.folds} by site, unseen sites): "
          f"MAE={oof_metrics['mae']:.3f} RMSE={oof_metrics['rmse']:.3f} "
          f"R2={oof_metrics['r2']:.4f} Spearman={oof_metrics['spearman']:.4f}")
    print(f"  (label-noise floor for OOF MAE: {noise_floor:.2f} — values near it "
          f"mean the expert surface is fully learned)")
    print(f"Rules baseline on same OOF folds: MAE={oof_metrics['rules_mae']:.3f}")
    if "eval" in metrics:
        e = metrics["eval"]
        print(f"Held-out eval sites vs noise-free labels: MAE={e['mae']:.3f} "
              f"Spearman={e['spearman']:.4f} | constant-5 baseline MAE={e['constant5_mae']:.3f} "
              f"| model-vs-rules MAE={e['model_vs_rules_mae']:.3f}")

    bundle = {
        "model": final_model,
        "feature_names": FEATURE_NAMES,
        "monotonic_cst": MONOTONIC_CST,
        "model_version": MODEL_VERSION,
        "schema_version": SCHEMA_VERSION,
        "sklearn_version": sklearn.__version__,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "params": {k: v for k, v in PARAMS.items() if k != "monotonic_cst"},
        "metrics": metrics,
        "label_sigma": args.sigma,
        "band_edges": BAND_EDGES,
        "categories": CATEGORIES,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out, compress=3)
    print(f"\n[done] artifact saved: {out}")
    print(f"[done] train rows={len(train_df)} sites={train_df['site_id'].nunique()} "
          f"features={len(FEATURE_NAMES)} sklearn={sklearn.__version__}")

    print("\n=== MODEL.md metrics block (paste into backend/MODEL.md) ===")
    print(f"```")
    print(f"trained_at:        {bundle['trained_at']}")
    print(f"train rows/sites:  {len(train_df)} / {train_df['site_id'].nunique()}")
    print(f"OOF MAE:           {oof_metrics['mae']:.3f}  (noise floor {noise_floor:.2f})")
    print(f"OOF R2:            {oof_metrics['r2']:.4f}")
    print(f"OOF Spearman:      {oof_metrics['spearman']:.4f}")
    if "eval" in metrics:
        print(f"Eval MAE:          {metrics['eval']['mae']:.3f} (noise-free labels, unseen sites)")
        print(f"Eval Spearman:     {metrics['eval']['spearman']:.4f}")
    print(f"final iters:       {final_iter} (folds: {n_iters})")
    print(f"```")


if __name__ == "__main__":
    main()

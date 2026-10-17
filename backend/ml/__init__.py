"""SwampHacks XII hazard-index ML model.

Pipeline: raw site-day dict -> schema.normalize -> rules.score_site (expert
sub-scores) / schema.build_features -> HistGradientBoostingRegressor (trained
by ml/train.py on synthetic site-days) -> 0-10 hazard index.
"""

MODEL_VERSION = "hazard-hgb-1.0"
SCHEMA_VERSION = "1.0.0"

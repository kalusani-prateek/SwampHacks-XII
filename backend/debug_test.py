# Exactly replicate what happens in selftest.py main()
import sys
sys.path.insert(0, '.')

# This is what _load_bundle() does
from pathlib import Path
ARTIFACT = Path(__file__).resolve().parent.parent / 'artifacts' / 'hazard_model.joblib'
print('[debug] ARTIFACT:', ARTIFACT)
print('[debug] ARTIFACT.exists():', ARTIFACT.exists())

bundle = None
if ARTIFACT.exists():
    import joblib
    bundle = joblib.load(ARTIFACT)
    print('[debug] Bundle loaded successfully')

print('[debug] Returning bundle:', 'Yes' if bundle is not None else 'No')

# Now let's see what happens when we import model and use it
import backend.ml.model as model
print('[debug] After import - model.ARTIFACT_PATH:', model.ARTIFACT_PATH)
print('[debug] After import - model.ARTIFACT_PATH.exists():', model.ARTIFACT_PATH.exists())
print('[debug] After import - model._BUNDLE:', model._BUNDLE)

# Test load_model
print('[debug] Testing load_model')
loaded = model.load_model()
print('[debug] After load_model - loaded:', 'Yes' if loaded is not None else 'No')
if loaded is not None:
    print('[debug] After load_model - model version:', loaded.get('model_version', 'Not found'))

# Test predict_site with a simple case
from ml.schema import normalize
from ml import rules
test_input = {'site_id': 'T', 'temp_max_c': 22.0, 'temp_min_c': 15.0,
              'relative_humidity_pct': 50.0, 'wind_max_kmh': 8.0, 'precip_total_mm': 0.0,
              'precip_intensity_max_mmh': 0.0, 'severe_weather_flag': False,
              'visibility_km': 15.0, 'lightning_min_distance_km': 90.0,
              'minutes_since_last_strike_min': None, 'rain_prev_72h_mm': 0.0,
              'soil_moisture_pct': 45.0, 'river_stage_above_normal_m': 0.2,
              'distance_to_river_m': 25000.0, 'elevation_above_river_m': 10.0,
              'is_wetland': False, 'wildlife_sightings_24h': 0,
              'wildlife_sightings_7d': 0, 'wildlife_max_threat_level': 0.0}

print('[debug] Testing predict_site')
report = model.predict_site(test_input)
print('[debug] Report model_version:', report.get('model_version', 'Not found'))
print('[debug] Report hazard_index:', report.get('hazard_index', 'Not found'))
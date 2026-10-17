from pathlib import Path
ARTIFACT_PATH = Path(__file__).resolve().parent / "artifacts" / "hazard_model.joblib"
print('ARTIFACT_PATH:', ARTIFACT_PATH)
print('Exists:', ARTIFACT_PATH.exists())
print('Parent dir:', Path(__file__).resolve().parent)
"""Shared test fixtures: a fresh app + in-memory database per test, no network, no background jobs."""
import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.security import limiter  # noqa: E402
from config import TestConfig  # noqa: E402

DEMO_PASSWORD = TestConfig.DEMO_PASSWORD


@pytest.fixture
def app(tmp_path):
    class Config(TestConfig):
        UPLOAD_FOLDER = tmp_path / "uploads"
        FRONTEND_DIST = tmp_path / "dist"

    limiter._hits.clear()  # rate-limit counters are per process
    application = create_app(Config)
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username, password=DEMO_PASSWORD):
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.get_json()
    return response


@pytest.fixture
def supervisor(client):
    login(client, "supervisor")
    return client


@pytest.fixture
def crew(client):
    login(client, "crew")
    return client


def sample_weather(today, heat=88.0, gust=18.0, rain_24h=0.1, soil=0.25, cape=300.0, code=1, humidity_min=55):
    """An Open-Meteo summary (the shape services/weather.py stores) with chosen readings."""
    days = [{
        "date": (today + timedelta(days=offset)).isoformat(),
        "tempMaxF": heat - 8,
        "heatIndexMaxF": heat,
        "precipIn": 0.1,
        "precipHours": 1,
        "gustMaxMph": gust,
        "windMaxMph": gust / 2,
        "weatherCode": code,
        "humidityMinPct": humidity_min,
        "capeMax": cape,
    } for offset in range(-1, 8)]
    return {
        "fetchedAt": "2026-10-17T12:00:00Z",
        "timezone": "America/New_York",
        "current": {"time": f"{today.isoformat()}T12:00", "tempF": heat - 8, "humidityPct": 60, "heatIndexF": heat,
                    "precipIn": 0, "weatherCode": code, "windMph": gust / 2, "gustMph": gust},
        "precip24hIn": rain_24h,
        "soilMoisture": soil,
        "heatIndexNext12hF": heat,
        "gustNext12hMph": gust,
        "capeNext12h": cape,
        "daily": days,
        "todayIndex": 1,
    }

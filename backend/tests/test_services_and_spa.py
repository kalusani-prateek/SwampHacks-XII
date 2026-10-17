"""Data-source parsers (offline) and serving the built frontend."""
from datetime import datetime
from types import SimpleNamespace

from app.services import fires, lightning, rivers, weather


def test_weather_summary_from_an_open_meteo_response():
    hours = [f"2026-10-17T{h:02d}:00" for h in range(24)] + [f"2026-10-18T{h:02d}:00" for h in range(24)]
    item = {
        "timezone": "America/New_York",
        "current": {"time": "2026-10-17T14:15", "temperature_2m": 90, "apparent_temperature": 101, "wind_gusts_10m": 20},
        "hourly": {
            "time": hours,
            "precipitation": [0.1] * 48,
            "apparent_temperature": [100 + (h == 18) * 6 for h in range(48)],
            "wind_gusts_10m": [22] * 48,
            "soil_moisture_3_to_9cm": [0.31] * 48,
            "cape": [800] * 48,
        },
        "daily": {"time": ["2026-10-16", "2026-10-17", "2026-10-18"], "apparent_temperature_max": [99, 106, 97]},
    }
    summary = weather.summarize(item)
    assert summary["todayIndex"] == 1
    assert summary["precip24hIn"] == 1.5           # 15 hours of 0.1" so far today
    assert summary["heatIndexNext12hF"] == 106      # the 6 PM peak
    assert summary["soilMoisture"] == 0.31
    assert summary["daily"][1]["heatIndexMaxF"] == 106


def test_lightning_flashes_are_matched_to_nearby_sites():
    site = SimpleNamespace(id="turkey-point", lat=25.4356, lng=-80.3308)
    when = datetime(2026, 10, 17, 12, 0)
    flashes = [(25.50, -80.33, when), (27.0, -80.33, when), (-6.7, -75.0, when)]
    matches = lightning.match_sites([site], flashes)
    assert len(matches) == 1 and matches[0][0] == "turkey-point" and matches[0][2] < 5


def test_nearest_fire_distance():
    site = SimpleNamespace(id="palo-verde", lat=33.388, lng=-112.862)
    result = fires.nearest_by_site([site], [(33.45, -112.86), (40.0, -100.0)])["palo-verde"]
    assert 4 < result["nearestMiles"] < 5 and result["within25mi"] == 1


def test_river_gauges_on_the_named_waterway_are_preferred():
    assert rivers.waterway_keyword("Mississippi River") == "mississippi"
    assert rivers.waterway_keyword("St. Johns River") == "johns"
    assert rivers.waterway_keyword(None) is None


def test_unknown_api_paths_return_json_404(client):
    response = client.get("/api/nope")
    assert response.status_code == 404 and response.get_json() == {"message": "Not found"}


def test_frontend_routes_fall_back_to_index_html(app, client):
    dist = app.config["FRONTEND_DIST"]
    assert "npm run build" in client.get("/").get_data(as_text=True)  # not built yet
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<div id=root></div>")
    assert client.get("/manage/users").get_data(as_text=True) == "<div id=root></div>"


def test_meta_reports_features(client):
    meta = client.get("/api/meta").get_json()
    assert meta["api"] == "planit-control" and meta["assistant"] is False
    assert meta["demoAccounts"]["usernames"] == ["supervisor", "crew"]

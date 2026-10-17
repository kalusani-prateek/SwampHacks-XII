"""Rule-based hazard scoring (pure functions, no database)."""
from datetime import date, datetime, timedelta

from conftest import sample_weather

from app.services.hazards import combine, level, ramp, score_site

RULES = {"lightningRadiusMiles": 10, "lightningAllClearMinutes": 30, "floodRainInches": 2,
         "heatIndexF": 105, "windMph": 35, "hazardIndexAlert": 7.5}
NOW = datetime(2026, 10, 17, 16, 0)


def score(weather=None, strikes=(), crew_wildlife=0, **readings):
    site = {"waterway": readings.pop("waterway", None), "weather": weather, **readings}
    return score_site(site, list(strikes), crew_wildlife, RULES, NOW)


def test_ramp_interpolates_and_clamps():
    points = [(80, 0), (90, 3), (103, 6)]
    assert ramp(70, points) == 0
    assert ramp(85, points) == 1.5
    assert ramp(200, points) == 6
    assert ramp(None, points) == 0


def test_combine_is_driven_by_the_worst_hazard():
    calm = dict.fromkeys(["heat", "lightning", "flooding", "wildfire", "soil", "wildlife", "wind"], 0.0)
    assert combine(calm) == 0
    assert combine({**calm, "heat": 10}) >= 6
    assert level(2)["decision"] == "GO" and level(6)["decision"] == "CAUTION" and level(8)["decision"] == "NO-GO"


def test_heat_and_wind_scores_follow_breakpoints():
    result = score(sample_weather(date(2026, 10, 17), heat=112, gust=40))
    assert 8 <= result["hazards"]["heat"] <= 9
    assert result["hazards"]["wind"] == 7.0
    assert any("Heat index up to 112°F" in d for d in result["drivers"])
    assert result["conditions"]["windGustMph"] == 40


def test_lightning_within_radius_means_stop_work():
    strikes = [{"observedAt": NOW - timedelta(minutes=4), "distance": 3.2}]
    result = score(sample_weather(date(2026, 10, 17)), strikes)
    assert result["lightning"]["stopWork"] is True
    assert result["hazards"]["lightning"] == 10
    assert result["hazardIndex"] >= 8
    assert result["drivers"][0].startswith("Lightning 3 mi away 4 min ago")


def test_all_clear_after_the_window_passes():
    strikes = [{"observedAt": NOW - timedelta(minutes=31), "distance": 3.2}]
    result = score(sample_weather(date(2026, 10, 17)), strikes)
    assert result["lightning"]["stopWork"] is False


def test_official_nws_warnings_set_minimum_scores():
    nws = {"alerts": [{"event": "Flash Flood Warning", "headline": "Flash Flood Warning until 8 PM"}]}
    result = score(sample_weather(date(2026, 10, 17)), nws=nws)
    assert result["hazards"]["flooding"] >= 8.5
    assert result["hazardIndex"] >= 8.5
    assert "NWS Flash Flood Warning" in result["drivers"]


def test_river_rise_counts_only_for_waterway_sites():
    river = {"gaugeName": "Mississippi River At Clinton", "stageFt": 15, "change24hFt": 4}
    on_river = score(sample_weather(date(2026, 10, 17)), waterway="Mississippi River", river=river)
    inland = score(sample_weather(date(2026, 10, 17)), river=river)
    assert on_river["hazards"]["flooding"] > 6 and inland["hazards"]["flooding"] < 2


def test_fire_and_wildlife_inputs():
    result = score(sample_weather(date(2026, 10, 17)), crew_wildlife=1,
                   fire={"nearestMiles": 4}, wildlife={"count30d": 5, "recent": [{"name": "American Alligator"}]})
    assert result["hazards"]["wildfire"] == 9
    assert result["hazards"]["wildlife"] == 7
    assert result["conditions"]["nearestFireMiles"] == 4


def test_forecast_covers_the_next_seven_days():
    today = date(2026, 10, 17)
    result = score(sample_weather(today, heat=110, code=95))
    assert len(result["forecast"]) == 7
    assert result["forecast"][0]["date"] == (today + timedelta(days=1)).isoformat()
    assert result["forecast"][0]["topHazard"] == "heat"


def test_no_data_yet_scores_zero_without_crashing():
    result = score(None)
    assert result["hazardIndex"] == 0
    assert result["drivers"] == ["No significant hazards right now"]

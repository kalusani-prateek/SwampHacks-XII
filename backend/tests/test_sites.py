"""Job sites: seeded from EIA-860M, readable slugs, supervisor management."""


def test_all_58_eia_sites_are_seeded(crew):
    sites = crew.get("/api/sites").get_json()["sites"]
    assert len(sites) == 58
    turkey = next(s for s in sites if s["id"] == "turkey-point")
    assert turkey["eiaPlantId"] == 621
    assert turkey["utility"] == "Florida Power & Light Co"
    assert set(turkey["hazards"]) == {"heat", "lightning", "flooding", "wildfire", "soil", "wildlife", "wind"}
    assert turkey["scoring"]["method"] == "rule-based"


def test_unknown_or_malformed_site_ids_404(crew):
    assert crew.get("/api/sites/no-such-plant").status_code == 404
    assert crew.get("/api/sites/Turkey%20Point").status_code == 404


def test_supervisor_adds_site_with_readable_unique_id(supervisor):
    body = {"name": "Big Bend", "state": "FL", "lat": 27.79, "lng": -82.40, "timezone": "America/New_York"}
    response = supervisor.post("/api/sites", json=body)
    assert response.status_code == 201
    assert response.get_json()["site"]["id"] == "big-bend-2"  # "big-bend" already exists
    assert supervisor.post("/api/sites", json={**body, "lat": 200}).status_code == 400
    assert supervisor.post("/api/sites", json={**body, "timezone": "Mars/Base"}).status_code == 400


def test_paused_sites_are_hidden_from_crew(supervisor, app):
    assert supervisor.put("/api/sites/deerhaven", json={"active": False}).status_code == 200
    everything = supervisor.get("/api/sites?includeInactive=true").get_json()["sites"]
    assert any(s["id"] == "deerhaven" and not s["active"] for s in everything)
    supervisor.post("/api/auth/logout")
    supervisor.post("/api/auth/login", json={"username": "crew", "password": app.config["DEMO_PASSWORD"]})
    assert all(s["id"] != "deerhaven" for s in supervisor.get("/api/sites").get_json()["sites"])
    assert supervisor.get("/api/sites/deerhaven").status_code == 404


def test_supervisor_deletes_site(supervisor):
    assert supervisor.delete("/api/sites/colstrip").status_code == 200
    assert supervisor.get("/api/sites/colstrip").status_code == 404


def test_stats(supervisor):
    stats = supervisor.get("/api/stats").get_json()["stats"]
    assert stats["sites"] == 58 and stats["users"] == 2

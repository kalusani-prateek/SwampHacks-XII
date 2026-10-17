"""Crew hazard reports: photo uploads, validation, moderation."""
import io

from app.models import HazardReport

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def report(client, **overrides):
    data = {"siteId": "turkey-point", "type": "wildlife", "description": "Gator by the canal",
            "lat": "25.43", "lng": "-80.33", **overrides}
    return client.post("/api/reports", data=data, content_type="multipart/form-data")


def test_report_with_photo_is_saved_and_served(app, crew):
    response = report(crew, photo=(io.BytesIO(PNG), "gator.png"))
    assert response.status_code == 201
    created = response.get_json()["report"]
    assert created["reportedBy"] == "crew" and created["photoUrl"].endswith(".png")
    assert crew.get(created["photoUrl"]).status_code == 200
    assert app.test_client().get(created["photoUrl"]).status_code == 401  # photos need a signed-in user


def test_non_images_and_bad_input_are_rejected(crew):
    assert report(crew, photo=(io.BytesIO(b"MZ fake exe"), "evil.png")).status_code == 400
    assert report(crew, type="banana").status_code == 400
    assert report(crew, description="").status_code == 400
    assert report(crew, lat="999").status_code == 400
    assert report(crew, siteId="nowhere").status_code == 400


def test_crew_wildlife_report_raises_the_wildlife_score(crew):
    before = crew.get("/api/sites/turkey-point").get_json()["site"]["hazards"]["wildlife"]
    report(crew)
    after = crew.get("/api/sites/turkey-point").get_json()["site"]["hazards"]["wildlife"]
    assert before == 0 and after == 7


def test_supervisor_moderates_reports(app, client):
    from conftest import login
    login(client, "crew")
    report_id = report(client).get_json()["report"]["id"]
    assert client.patch(f"/api/reports/{report_id}", json={"status": "verified"}).status_code == 403
    client.post("/api/auth/logout")
    login(client, "supervisor")
    assert client.patch(f"/api/reports/{report_id}", json={"status": "verified"}).get_json()["report"]["status"] == "verified"
    assert client.patch(f"/api/reports/{report_id}", json={"status": "lost"}).status_code == 400
    with app.app_context():
        assert HazardReport.query.count() == 1


def test_uploads_only_serve_stored_names(crew):
    assert crew.get("/api/uploads/..%2Fconfig.py").status_code == 404

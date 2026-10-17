"""Crew hazard reports: photo uploads, validation, search, editing, moderation."""
import io
from datetime import timedelta

from conftest import login

from app.extensions import db
from app.models import HazardReport, utcnow

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def report(client, **overrides):
    data = {"siteId": "turkey-point", "type": "wildlife", "description": "Gator by the canal",
            "lat": "25.43", "lng": "-80.33", **overrides}
    return client.post("/api/reports", data=data, content_type="multipart/form-data")


def second_crew_member(app):
    """Another crew account, signed in on its own client."""
    other = app.test_client()
    body = {"username": "second", "email": "second@example.com", "password": "longenough", "siteId": "grand-gulf"}
    assert other.post("/api/auth/register", json=body).status_code == 201
    return other


def test_everyone_can_search_recent_reports(app, client):
    login(client, "crew")
    report(client)
    report(client, type="flooding", description="Water over the haul road (100% blocked)")
    client.post("/api/auth/logout")
    login(client, "supervisor")
    report(client, siteId="grand-gulf", type="debris", description="Fallen tree at the gate")
    with app.app_context():  # make the supervisor's report 40 days old
        HazardReport.query.filter_by(type="debris").one().created_at = utcnow() - timedelta(days=40)
        db.session.commit()

    def found(**query):
        return [r["description"] for r in client.get("/api/reports", query_string=query).get_json()["reports"]]

    gator, water, tree = "Gator by the canal", "Water over the haul road (100% blocked)", "Fallen tree at the gate"
    assert found() == [water, gator, tree]  # newest first
    assert found(type="wildlife") == [gator]
    assert found(q="GATOR") == [gator]  # case-insensitive
    assert found(q="grand gulf") == [tree]  # site names match
    assert found(q="crew") == [water, gator]  # reporter names match
    assert found(q="%") == [water] and found(q="_") == []  # LIKE wildcards are matched literally
    assert found(days=30) == [water, gator]
    assert found(mine="true") == [tree]
    assert client.get("/api/reports?days=0").status_code == 400


def test_reporter_edits_and_deletes_their_own_report(app, crew):
    created = report(crew, photo=(io.BytesIO(PNG), "gator.png")).get_json()["report"]
    assert created["canEdit"] is True
    url = f"/api/reports/{created['id']}"
    edited = crew.patch(url, json={"type": "debris", "description": " Just a log ", "lat": 25.44, "lng": -80.34})
    assert edited.status_code == 200
    assert {k: edited.get_json()["report"][k] for k in ("type", "description", "lat")} == \
        {"type": "debris", "description": "Just a log", "lat": 25.44}
    photo = app.config["UPLOAD_FOLDER"] / created["photoUrl"].rsplit("/", 1)[-1]
    assert photo.exists()
    assert crew.patch(url, json={"removePhoto": True}).get_json()["report"]["photoUrl"] is None
    assert not photo.exists()
    assert crew.patch(url, json={"status": "verified"}).status_code == 403  # status is for supervisors
    assert crew.delete(url).status_code == 200
    assert crew.get("/api/reports").get_json()["reports"] == []


def test_other_crew_can_see_but_not_change_someone_elses_report(app, crew):
    report_id = report(crew).get_json()["report"]["id"]
    other = second_crew_member(app)
    listed = other.get("/api/reports").get_json()["reports"]
    assert [r["id"] for r in listed] == [report_id] and listed[0]["canEdit"] is False
    assert other.patch(f"/api/reports/{report_id}", json={"description": "Mine now"}).status_code == 403
    assert other.delete(f"/api/reports/{report_id}").status_code == 403


def test_supervisor_can_edit_and_delete_any_report(client):
    login(client, "crew")
    report_id = report(client).get_json()["report"]["id"]
    client.post("/api/auth/logout")
    login(client, "supervisor")
    assert client.get("/api/reports").get_json()["reports"][0]["canEdit"] is True
    changed = client.patch(f"/api/reports/{report_id}", json={"description": "Gator relocated", "status": "resolved"})
    assert changed.status_code == 200
    assert {k: changed.get_json()["report"][k] for k in ("description", "status")} == \
        {"description": "Gator relocated", "status": "resolved"}
    assert client.delete(f"/api/reports/{report_id}").status_code == 200
    assert client.delete(f"/api/reports/{report_id}").status_code == 404


def test_edits_are_validated(crew):
    url = f"/api/reports/{report(crew).get_json()['report']['id']}"
    assert crew.patch(url, json={"type": "banana"}).status_code == 400
    assert crew.patch(url, json={"description": "   "}).status_code == 400
    assert crew.patch(url, json={"lat": 999}).status_code == 400
    assert crew.patch("/api/reports/9999", json={"description": "x"}).status_code == 404


def test_removing_a_wildlife_report_lowers_the_wildlife_score(crew):
    def wildlife():
        return crew.get("/api/sites/turkey-point").get_json()["site"]["hazards"]["wildlife"]

    first, second = (report(crew).get_json()["report"]["id"] for _ in range(2))
    assert wildlife() == 7
    crew.patch(f"/api/reports/{first}", json={"type": "debris"})  # no longer wildlife
    crew.delete(f"/api/reports/{second}")
    assert wildlife() == 0


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

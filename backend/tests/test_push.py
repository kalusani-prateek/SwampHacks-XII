"""Phone and desktop notifications (Web Push), with the push service replaced by a recorder."""
import json
from base64 import urlsafe_b64decode
from types import SimpleNamespace

import pytest
from conftest import login
from pywebpush import WebPushException

from app.extensions import db
from app.models import Notification, PushSubscription, Site, User
from app.services import briefings, ingest, push


@pytest.fixture
def sent(monkeypatch):
    """Every message 'posted' to a push service: [(endpoint, payload dict)]."""
    messages = []
    monkeypatch.setattr(push, "_send", lambda info, payload, key, claims: messages.append((info["endpoint"], json.loads(payload))))
    monkeypatch.setattr(push, "_last_no_go", {})
    return messages


def subscribe(client, device):
    body = {"endpoint": f"https://push.example.com/{device}", "keys": {"p256dh": "B" * 87, "auth": "a" * 22}}
    return client.post("/api/push/subscriptions", json=body)


def second_member(app, username="diver", site="turkey-point"):
    other = app.test_client()
    body = {"username": username, "email": f"{username}@example.com", "password": "longenough", "siteId": site}
    assert other.post("/api/auth/register", json=body).status_code == 201
    return other


def test_public_key_is_a_p256_point(client):
    key = client.get("/api/push/key").get_json()["publicKey"]
    raw = urlsafe_b64decode(key + "=" * (-len(key) % 4))
    assert len(raw) == 65 and raw[0] == 4  # uncompressed EC point, as browsers expect
    assert client.get("/api/push/key").get_json()["publicKey"] == key  # the same key every time


def test_devices_turn_notifications_on_and_off(app, crew):
    assert crew.post("/api/push/subscriptions", json={"endpoint": "http://insecure"}).status_code == 400
    assert subscribe(crew, "phone").status_code == 201
    assert subscribe(crew, "phone").status_code == 201  # same browser again: still one row
    with app.app_context():
        assert PushSubscription.query.count() == 1
    assert crew.delete("/api/push/subscriptions", json={"endpoint": "https://push.example.com/phone"}).status_code == 200
    with app.app_context():
        assert PushSubscription.query.count() == 0
    assert subscribe(app.test_client(), "x").status_code == 401  # must be signed in


def test_new_report_notifies_everyone_at_that_site_but_the_reporter(app, crew, sent):
    subscribe(crew, "crew-phone")
    teammate = second_member(app, "teammate", "turkey-point")
    subscribe(teammate, "teammate-phone")
    elsewhere = second_member(app, "faraway", "palo-verde")
    subscribe(elsewhere, "faraway-phone")

    form = {"siteId": "turkey-point", "type": "wildlife", "description": "Gator by the canal", "lat": "25.43", "lng": "-80.33"}
    assert crew.post("/api/reports", data=form, content_type="multipart/form-data").status_code == 201
    reports = [(endpoint, msg) for endpoint, msg in sent if msg["tag"].startswith("report-")]
    assert [endpoint for endpoint, _ in reports] == ["https://push.example.com/teammate-phone"]
    message = reports[0][1]
    assert message["title"] == "New hazard report at Turkey Point"
    assert message["body"] == "Wildlife: Gator by the canal (from crew)" and message["url"] == "/reports?site=turkey-point"


def test_site_turning_no_go_notifies_its_crew_once_an_hour(app, crew, sent):
    subscribe(crew, "crew-phone")
    with app.app_context():
        site = db.session.get(Site, "turkey-point")
        assert site.hazard_index < 7.5
        ingest.simulate_strike(site)  # lightning 3 mi away: stop work, index >= 8
        ingest.simulate_strike(site)  # still NO-GO: no second notification
    no_go = [msg for _, msg in sent if msg["tag"] == "nogo-turkey-point"]
    assert len(no_go) == 1
    assert no_go[0]["title"] == "⛔ Turkey Point is NO-GO" and no_go[0]["url"] == "/sites/turkey-point"
    assert "Lightning" in no_go[0]["body"]


def test_briefings_notify_each_person_about_their_own_site(app, crew, sent):
    subscribe(crew, "crew-phone")
    elsewhere = second_member(app, "faraway", "palo-verde")
    subscribe(elsewhere, "faraway-phone")
    with app.app_context():
        for site in Site.query.all():  # give every site a forecast so briefings can be built
            site.forecast = [{"date": "2026-10-18", "hazardIndex": 6.2, "topHazard": "heat",
                              "hazards": {"heat": 6.2, "lightning": 2, "flooding": 0, "wildfire": 0, "soil": 1, "wildlife": 0, "wind": 1}}]
        db.session.commit()
        briefings.send_now(["turkey-point", "palo-verde"])
    briefing = {endpoint: msg for endpoint, msg in sent if msg["tag"].startswith("briefing-")}
    assert briefing["https://push.example.com/crew-phone"]["title"] == "Tomorrow at Turkey Point: CAUTION"
    assert briefing["https://push.example.com/faraway-phone"]["title"] == "Tomorrow at Palo Verde: CAUTION"
    assert briefing["https://push.example.com/crew-phone"]["url"] == "/briefings"


def test_expired_devices_are_forgotten_and_attempts_are_logged(app, crew, monkeypatch):
    subscribe(crew, "old-phone")

    def gone(info, payload, key, claims):
        raise WebPushException("Gone", response=SimpleNamespace(status_code=410, text="expired"))

    monkeypatch.setattr(push, "_send", gone)
    assert crew.post("/api/push/test").status_code == 200
    with app.app_context():
        assert PushSubscription.query.count() == 0
        logged = Notification.query.filter_by(channel="push").one()
        assert logged.status == "failed" and logged.recipient == "crew"


def test_test_notification(app, crew, sent):
    assert crew.post("/api/push/test").status_code == 404  # no devices yet
    subscribe(crew, "laptop")
    response = crew.post("/api/push/test")
    assert response.status_code == 200 and response.get_json()["devices"] == 1
    assert sent[-1][1]["title"] == "PlanIT test notification"
    with app.app_context():
        assert Notification.query.filter_by(channel="push", status="sent").count() == 1


def test_deleting_an_account_removes_its_devices(app, client, sent):
    other = second_member(app, "leaver")
    subscribe(other, "leaver-phone")
    login(client, "supervisor")
    with app.app_context():
        user_id = User.query.filter_by(username="leaver").one().id
    assert client.delete(f"/api/users/{user_id}").status_code == 200
    with app.app_context():
        assert PushSubscription.query.count() == 0

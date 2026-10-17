"""Alert engine: lightning stop-work and all-clear, flood/heat/wind rules, per-user acknowledgement."""
from datetime import timedelta

from conftest import login, sample_weather

from app.extensions import db
from app.models import Alert, LightningStrike, Notification, Site, utcnow
from app.services import briefings, ingest


def active_alerts(client, site_id):
    return client.get(f"/api/alerts?active=true&siteId={site_id}").get_json()["alerts"]


def test_simulated_strike_raises_stop_work_and_countdown(supervisor):
    status = supervisor.post("/api/sites/turkey-point/lightning/simulate").get_json()
    assert status["distanceMiles"] == 3.0 and status["lastStrikeAt"].endswith("Z")
    alerts = active_alerts(supervisor, "turkey-point")
    assert [a["severity"] for a in alerts if a["type"] == "lightning"] == ["stop-work"]
    site = supervisor.get("/api/sites/turkey-point").get_json()["site"]
    assert site["hazards"]["lightning"] == 10 and site["hazardIndex"] >= 8


def test_lightning_alert_clears_after_the_all_clear_window(app, supervisor):
    supervisor.post("/api/sites/turkey-point/lightning/simulate")
    with app.app_context():
        strike = LightningStrike.query.filter_by(site_id="turkey-point").one()
        strike.observed_at = utcnow() - timedelta(minutes=31)
        db.session.commit()
        ingest.rescore_lightning_sites()
    assert not [a for a in active_alerts(supervisor, "turkey-point") if a["type"] == "lightning"]


def test_new_strike_restarts_the_countdown(app, supervisor):
    supervisor.post("/api/sites/grand-gulf/lightning/simulate")
    with app.app_context():
        LightningStrike.query.update({"observed_at": utcnow() - timedelta(minutes=20)})
        db.session.commit()
    latest = supervisor.post("/api/sites/grand-gulf/lightning/simulate").get_json()["lastStrikeAt"]
    with app.app_context():
        newest = max(s.observed_at for s in LightningStrike.query.filter_by(site_id="grand-gulf"))
    assert latest.startswith(newest.isoformat()[:16])


def test_stop_work_alerts_are_sent_to_the_outbox(app, supervisor):
    supervisor.post("/api/sites/turkey-point/lightning/simulate")
    with app.app_context():
        sent = Notification.query.all()
    assert sent and all(n.status == "logged" for n in sent)  # no SMTP configured: recorded only
    assert any("STOP WORK" in (n.subject or "") for n in sent)


def test_flood_heat_and_wind_rules(app, supervisor):
    with app.app_context():
        site = db.session.get(Site, "grand-gulf")  # on the Mississippi River
        site.weather = sample_weather(briefings.local_now(site).date(), heat=110, gust=45, rain_24h=3.0)
        db.session.commit()
        ingest.rescore([site])
    kinds = {a["type"]: a for a in active_alerts(supervisor, "grand-gulf")}
    assert {"flooding", "heat", "wind"} <= set(kinds)
    assert 'of rain in 24 h on the Mississippi River' in kinds["flooding"]["message"]


def test_acknowledgement_is_per_user(app, client):
    login(client, "supervisor")
    client.post("/api/sites/turkey-point/lightning/simulate")
    client.post("/api/auth/logout")
    login(client, "crew")
    alert = active_alerts(client, "turkey-point")[0]
    assert alert["acknowledged"] is False
    assert client.post(f"/api/alerts/{alert['id']}/ack").get_json()["alert"]["acknowledged"] is True
    client.post("/api/auth/logout")
    login(client, "supervisor")
    assert active_alerts(client, "turkey-point")[0]["acknowledged"] is False


def test_alert_stream_opens(crew):
    response = crew.get("/api/alerts/stream", buffered=False)
    assert response.mimetype == "text/event-stream"
    assert next(response.response).startswith(b"retry:")
    response.close()


def test_alerts_are_ordered_stop_work_first(app, supervisor):
    supervisor.post("/api/sites/turkey-point/lightning/simulate")
    with app.app_context():
        db.session.add(Alert(site_id="vogtle", key="heat", type="heat", severity="warning", title="Heat", message="m"))
        db.session.commit()
    severities = [a["severity"] for a in supervisor.get("/api/alerts?active=true").get_json()["alerts"]]
    assert severities[0] == "stop-work"

"""Next-day briefings (6 PM local), and supervisor settings validation."""
from conftest import sample_weather

from app.extensions import db
from app.models import Briefing, Notification, Site
from app.services import briefings, ingest
from app.settings_store import get_setting, set_setting


def give_forecast(app, site_id="turkey-point", **readings):
    with app.app_context():
        site = db.session.get(Site, site_id)
        site.weather = sample_weather(briefings.local_now(site).date(), **readings)
        db.session.commit()
        ingest.rescore([site])


def test_briefing_preview_uses_tomorrows_forecast(app, crew):
    give_forecast(app, heat=110)
    items = crew.get("/api/briefings").get_json()["briefings"]
    turkey = next(b for b in items if b["siteId"] == "turkey-point")
    assert turkey["generated"] is False
    assert turkey["topHazards"][0]["key"] == "heat"
    assert turkey["decision"] in {"GO", "CAUTION", "NO-GO"}


def test_send_now_stores_and_delivers_a_digest(app, supervisor):
    give_forecast(app)
    assert supervisor.post("/api/briefings", json={"siteIds": ["turkey-point"]}).get_json()["sent"] == 1
    with app.app_context():
        assert Briefing.query.filter_by(site_id="turkey-point").one().sent_at is not None
        emails = Notification.query.filter_by(channel="email").all()
    assert len(emails) == 2 and "next-day safety briefing" in emails[0].subject


def test_scheduled_briefings_run_once_per_site_per_day(app):
    give_forecast(app, "turkey-point")
    give_forecast(app, "grand-gulf")
    with app.app_context():
        settings = get_setting("briefing_settings")
        set_setting("briefing_settings", {**settings, "localTime": "00:00"})  # every site is past its send time
        assert briefings.run_due() == 2
        assert briefings.run_due() == 0


def test_alert_rule_validation(supervisor):
    ok = supervisor.put("/api/settings/alert-rules", json={"rules": {"windMph": 40}})
    assert ok.get_json()["rules"]["windMph"] == 40
    assert supervisor.put("/api/settings/alert-rules", json={"rules": {"heatIndexF": 500}}).status_code == 400


def test_briefing_settings_validation(supervisor):
    assert supervisor.put("/api/settings/briefings", json={"settings": {"localTime": "25:99"}}).status_code == 400
    assert supervisor.put("/api/settings/briefings", json={"settings": {"recipients": ["admin"]}}).status_code == 400
    saved = supervisor.put("/api/settings/briefings", json={"settings": {"localTime": "17:30", "recipients": ["supervisor"]}})
    assert saved.get_json()["settings"]["localTime"] == "17:30"

"""Designated sites (chosen at sign-up, changed in the account page) and self-service account changes."""
import sqlite3

from conftest import DEMO_PASSWORD, login
from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from app.models import Site, User
from config import TestConfig


def sign_up(client, **overrides):
    body = {"username": "newhand", "email": "newhand@example.com", "password": "longenough", "siteId": "grand-gulf",
            **overrides}
    return client.post("/api/auth/register", json=body)


def me(client):
    return client.get("/api/auth/me").get_json()["user"]


def test_sign_up_assigns_the_chosen_site(client):
    assert sign_up(client, siteId=None).get_json()["message"] == "Choose the site you work at."
    assert sign_up(client, siteId="nowhere").status_code == 400
    response = sign_up(client)
    assert response.status_code == 201
    assert {k: response.get_json()["user"][k] for k in ("siteId", "siteName")} == {"siteId": "grand-gulf", "siteName": "Grand Gulf"}
    assert me(client)["siteId"] == "grand-gulf"


def test_paused_sites_cannot_be_chosen(app, client):
    with app.app_context():
        db.session.get(Site, "grand-gulf").active = False
        db.session.commit()
    assert sign_up(client).status_code == 400


def test_site_choices_are_public_for_the_sign_up_form(client):
    sites = client.get("/api/sites/options").get_json()["sites"]
    assert len(sites) == 58 and set(sites[0]) == {"id", "name", "state"}


def test_demo_accounts_work_at_turkey_point(crew):
    assert me(crew)["siteId"] == "turkey-point"


def test_people_change_their_own_site_without_a_password(crew):
    url = f"/api/users/{me(crew)['id']}"
    changed = crew.put(url, json={"siteId": "palo-verde"})
    assert changed.status_code == 200 and changed.get_json()["user"]["siteName"] == "Palo Verde"
    assert crew.put(url, json={"siteId": "nowhere"}).status_code == 400
    assert me(crew)["siteId"] == "palo-verde"


def test_own_username_email_and_password_need_the_current_password(crew):
    url = f"/api/users/{me(crew)['id']}"
    new_details = {"username": "crew2", "email": "crew2@example.com", "password": "brand-new-pass"}
    assert crew.put(url, json=new_details).status_code == 400  # no current password
    assert crew.put(url, json={**new_details, "currentPassword": "not-my-password"}).status_code == 403
    changed = crew.put(url, json={**new_details, "currentPassword": DEMO_PASSWORD})
    assert changed.status_code == 200 and changed.get_json()["user"]["username"] == "crew2"
    crew.post("/api/auth/logout")
    assert crew.post("/api/auth/login", json={"username": "crew2", "password": DEMO_PASSWORD}).status_code == 401
    login(crew, "crew2", "brand-new-pass")


def test_supervisor_fixes_someone_elses_account_without_their_password(app, client):
    other = app.test_client()
    user_id = sign_up(other).get_json()["user"]["id"]
    login(client, "supervisor")
    changed = client.put(f"/api/users/{user_id}", json={"email": "fixed@example.com", "siteId": "palo-verde"})
    assert changed.status_code == 200
    assert {k: changed.get_json()["user"][k] for k in ("email", "siteId")} == {"email": "fixed@example.com", "siteId": "palo-verde"}
    assert other.put(f"/api/users/{user_id - 1}", json={"siteId": "palo-verde"}).status_code == 403  # crew: only yourself


def test_deleting_a_site_clears_it_for_people_who_worked_there(supervisor):
    site = {"name": "Test Yard", "state": "FL", "lat": 27.0, "lng": -81.0, "timezone": "America/New_York"}
    site_id = supervisor.post("/api/sites", json=site).get_json()["site"]["id"]
    supervisor.put(f"/api/users/{me(supervisor)['id']}", json={"siteId": site_id})
    assert me(supervisor)["siteId"] == site_id
    assert supervisor.delete(f"/api/sites/{site_id}").status_code == 200
    assert me(supervisor)["siteId"] is None


def test_older_databases_get_the_site_column(tmp_path):
    path = tmp_path / "old.db"
    with sqlite3.connect(path) as old:  # the users table as it was before designated sites
        old.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR(64) UNIQUE NOT NULL, "
                    "email VARCHAR(120) UNIQUE NOT NULL, password_hash VARCHAR(256) NOT NULL, "
                    "role VARCHAR(20) NOT NULL, phone VARCHAR(32))")
        old.execute("INSERT INTO users (username, email, password_hash, role) VALUES ('crew', 'crew@planit.dev', 'x', 'crew')")
    old.close()

    class Config(TestConfig):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{path.as_posix()}"
        UPLOAD_FOLDER = tmp_path / "uploads"
        FRONTEND_DIST = tmp_path / "dist"

    app = create_app(Config)
    with app.app_context():
        assert "site_id" in {column["name"] for column in inspect(db.engine).get_columns("users")}
        assert User.query.filter_by(username="crew").one().site_id == "turkey-point"  # demo account gets the demo site
        db.session.remove()
        db.engine.dispose()

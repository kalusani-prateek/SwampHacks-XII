"""Sign-in, and the two roles: supervisors hold every management privilege; there is no admin."""
from conftest import login


def test_login_returns_user_and_me_works(client):
    response = login(client, "supervisor")
    assert response.get_json()["user"]["role"] == "supervisor"
    assert client.get("/api/auth/me").get_json()["user"]["username"] == "supervisor"


def test_bad_password_and_signed_out_requests_are_rejected(client):
    assert client.post("/api/auth/login", json={"username": "crew", "password": "wrong"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/sites").status_code == 401


def test_register_creates_crew_and_rejects_duplicates(client):
    body = {"username": "newhand", "email": "newhand@example.com", "password": "longenough",
            "siteId": "turkey-point"}
    response = client.post("/api/auth/register", json=body)
    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "crew"
    assert client.get("/api/auth/me").get_json()["user"]["username"] == "newhand"  # signed in straight away
    assert client.post("/api/auth/register", json=body).status_code == 409
    assert client.post("/api/auth/register", json={**body, "username": "x"}).status_code == 400


def test_register_never_creates_a_supervisor(client):
    body = {"username": "sneaky", "email": "sneaky@example.com", "password": "longenough", "role": "supervisor",
            "siteId": "turkey-point"}
    assert client.post("/api/auth/register", json=body).get_json()["user"]["role"] == "crew"


def test_register_is_rate_limited(client):
    for i in range(5):
        body = {"username": f"crew{i}", "email": f"crew{i}@example.com", "password": "longenough", "siteId": "turkey-point"}
        assert client.post("/api/auth/register", json=body).status_code == 201
    body = {"username": "crew5", "email": "crew5@example.com", "password": "longenough", "siteId": "turkey-point"}
    assert client.post("/api/auth/register", json=body).status_code == 429


def test_logout_ends_the_session(crew):
    assert crew.post("/api/auth/logout").status_code == 200
    assert crew.get("/api/auth/me").status_code == 401


def test_crew_cannot_use_supervisor_endpoints(crew):
    assert crew.get("/api/users").status_code == 403
    assert crew.get("/api/stats").status_code == 403
    assert crew.get("/api/notifications").status_code == 403
    assert crew.get("/api/sites?includeInactive=true").status_code == 403
    assert crew.put("/api/settings/alert-rules", json={"rules": {"windMph": 40}}).status_code == 403
    assert crew.post("/api/sites", json={"name": "X", "lat": 1, "lng": 1}).status_code == 403
    assert crew.post("/api/briefings").status_code == 403
    assert crew.post("/api/sites/turkey-point/lightning/simulate").status_code == 403


def test_crew_can_read_field_data(crew):
    for path in ("/api/sites", "/api/sites/turkey-point", "/api/alerts", "/api/reports",
                 "/api/briefings", "/api/settings/alert-rules", "/api/sites/turkey-point/lightning"):
        assert crew.get(path).status_code == 200, path


def test_supervisor_manages_users(supervisor):
    users = supervisor.get("/api/users").get_json()["users"]
    assert {u["role"] for u in users} == {"supervisor", "crew"}
    created = supervisor.post("/api/users", json={"username": "lead2", "email": "lead2@example.com",
                                                   "password": "longenough", "role": "supervisor"})
    assert created.status_code == 201
    new_id = created.get_json()["user"]["id"]
    assert supervisor.put(f"/api/users/{new_id}", json={"role": "crew"}).get_json()["user"]["role"] == "crew"
    assert supervisor.post("/api/users", json={"username": "bad", "email": "b@example.com",
                                                "password": "longenough", "role": "admin"}).status_code == 400
    assert supervisor.delete(f"/api/users/{new_id}").status_code == 200


def test_the_last_supervisor_cannot_be_removed(supervisor):
    me = supervisor.get("/api/auth/me").get_json()["user"]
    assert supervisor.put(f"/api/users/{me['id']}", json={"role": "crew"}).status_code == 409
    assert supervisor.delete(f"/api/users/{me['id']}").status_code == 409


def test_crew_cannot_promote_themselves(crew):
    me = crew.get("/api/auth/me").get_json()["user"]
    assert crew.put(f"/api/users/{me['id']}", json={"role": "supervisor"}).status_code == 403
    assert crew.put(f"/api/users/{me['id']}", json={"phone": "+13055550123"}).status_code == 200


def test_there_is_no_admin_api(supervisor):
    assert supervisor.get("/api/admins/users").status_code == 404

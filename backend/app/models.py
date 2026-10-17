"""Database models.

Roles: "crew" and "supervisor" (supervisors hold every management privilege;
there is no admin role). Each site's latest readings from every data source,
and the scores computed from them, are stored as JSON columns on the Site row.
"""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager
from .services.hazards import HAZARD_KEYS, SCORING

ROLES = ("crew", "supervisor")
REPORT_TYPES = ("heat", "lightning", "flooding", "wildfire", "soil", "wildlife", "wind", "debris", "equipment", "other")
REPORT_STATUSES = ("open", "verified", "resolved", "dismissed")


def utcnow():
    """Current UTC time without tzinfo (SQLite stores naive datetimes)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso(value):
    """ISO 8601 UTC string with a Z suffix, or None."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="crew")
    phone = db.Column(db.String(32))  # optional, for SMS alerts

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_supervisor(self):
        return self.role == "supervisor"

    def to_dict(self):
        return {"id": self.id, "username": self.username, "email": self.email, "role": self.role, "phone": self.phone}


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Site(db.Model):
    __tablename__ = "sites"

    id = db.Column(db.String(80), primary_key=True)  # readable slug, e.g. "turkey-point"
    eia_plant_id = db.Column(db.Integer)
    name = db.Column(db.String(120), nullable=False)
    eia_name = db.Column(db.String(120))
    state = db.Column(db.String(2))
    county = db.Column(db.String(80))
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    utility = db.Column(db.String(160))
    plant_type = db.Column(db.String(80))
    capacity_mw = db.Column(db.Float)
    timezone = db.Column(db.String(64), nullable=False, default="America/New_York")
    waterway = db.Column(db.String(120))
    active = db.Column(db.Boolean, nullable=False, default=True)

    # Latest raw readings, replaced on each refresh.
    weather = db.Column(db.JSON)   # Open-Meteo current, hourly and daily forecast
    nws = db.Column(db.JSON)       # active National Weather Service alerts
    river = db.Column(db.JSON)     # nearest USGS stream gauge
    fire = db.Column(db.JSON)      # nearest NASA FIRMS fire detection
    wildlife = db.Column(db.JSON)  # iNaturalist sightings of dangerous species

    # Computed by services/hazards.py.
    hazard_index = db.Column(db.Float, nullable=False, default=0.0)
    hazards = db.Column(db.JSON)
    conditions = db.Column(db.JSON)
    drivers = db.Column(db.JSON)
    forecast = db.Column(db.JSON)
    scored_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            "id": self.id,
            "eiaPlantId": self.eia_plant_id,
            "name": self.name,
            "eiaName": self.eia_name,
            "state": self.state,
            "county": self.county,
            "lat": self.lat,
            "lng": self.lng,
            "utility": self.utility,
            "plantType": self.plant_type,
            "capacityMw": self.capacity_mw,
            "timezone": self.timezone,
            "waterway": self.waterway or None,
            "active": self.active,
            "hazardIndex": round(self.hazard_index or 0.0, 1),
            "hazards": self.hazards or {key: 0.0 for key in HAZARD_KEYS},
            "conditions": self.conditions or {},
            "drivers": self.drivers or ["Waiting for the first data refresh"],
            "updatedAt": iso(self.scored_at),
            "scoring": SCORING,
        }


class LightningStrike(db.Model):
    __tablename__ = "lightning_strikes"

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.String(80), db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    observed_at = db.Column(db.DateTime, nullable=False, index=True)
    distance_miles = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(20), nullable=False, default="glm")  # "glm" or "simulated"


class Alert(db.Model):
    __tablename__ = "alerts"

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.String(80), db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    key = db.Column(db.String(80), nullable=False)  # one active alert per (site, key)
    type = db.Column(db.String(20), nullable=False)  # hazard category, matches the frontend icons
    severity = db.Column(db.String(20), nullable=False)  # stop-work | warning | info
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    cleared_at = db.Column(db.DateTime)

    site = db.relationship("Site")
    acks = db.relationship("AlertAck", cascade="all, delete-orphan", backref="alert")

    def to_dict(self, user=None):
        return {
            "id": self.id,
            "siteId": self.site_id,
            "siteName": self.site.name if self.site else self.site_id,
            "type": self.type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "createdAt": iso(self.created_at),
            "updatedAt": iso(self.updated_at),
            "active": self.active,
            "acknowledged": bool(user and any(ack.user_id == user.id for ack in self.acks)),
        }


class AlertAck(db.Model):
    """A user confirming they have seen an alert (acknowledgement is per user)."""
    __tablename__ = "alert_acks"
    __table_args__ = (db.UniqueConstraint("alert_id", "user_id"),)

    id = db.Column(db.Integer, primary_key=True)
    alert_id = db.Column(db.Integer, db.ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class HazardReport(db.Model):
    __tablename__ = "hazard_reports"

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.String(80), db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    type = db.Column(db.String(20), nullable=False)
    description = db.Column(db.Text, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    photo_filename = db.Column(db.String(64))
    status = db.Column(db.String(20), nullable=False, default="open")
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)

    user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "siteId": self.site_id,
            "type": self.type,
            "description": self.description,
            "lat": self.lat,
            "lng": self.lng,
            "photoUrl": f"/api/uploads/{self.photo_filename}" if self.photo_filename else None,
            "reportedBy": self.user.username if self.user else "former user",
            "createdAt": iso(self.created_at),
            "status": self.status,
        }


class Briefing(db.Model):
    """A next-day safety briefing for one site, generated at 6 PM site-local time."""
    __tablename__ = "briefings"
    __table_args__ = (db.UniqueConstraint("site_id", "for_date"),)

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.String(80), db.ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    for_date = db.Column(db.Date, nullable=False)
    payload = db.Column(db.JSON, nullable=False)
    generated_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    sent_at = db.Column(db.DateTime)


class Setting(db.Model):
    """Supervisor-editable configuration stored as JSON (alert rules, briefing settings)."""
    __tablename__ = "settings"

    key = db.Column(db.String(64), primary_key=True)
    value = db.Column(db.JSON, nullable=False)


class Notification(db.Model):
    """Every outbound email/SMS. Without SMTP/Twilio settings they are only logged here (the outbox)."""
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow, index=True)
    channel = db.Column(db.String(10), nullable=False)  # email | sms
    recipient = db.Column(db.String(160), nullable=False)
    subject = db.Column(db.String(200))
    body = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(10), nullable=False)  # sent | logged | failed
    error = db.Column(db.Text)

    def to_dict(self):
        return {
            "id": self.id,
            "createdAt": iso(self.created_at),
            "channel": self.channel,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "status": self.status,
            "error": self.error,
        }

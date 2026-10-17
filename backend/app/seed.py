"""Create tables and seed the job sites (data/sites.csv), settings and demo accounts."""
import csv
import logging
from pathlib import Path

from sqlalchemy import event, inspect, text

from .extensions import db
from .models import Setting, Site, User
from .settings_store import DEFAULTS

log = logging.getLogger(__name__)
SITES_CSV = Path(__file__).resolve().parent.parent / "data" / "sites.csv"
DEMO_SITE = "turkey-point"  # the brief's scenario: the demo accounts work here


def enable_sqlite_wal(engine):
    """WAL journal mode lets the web server read while background jobs write."""
    if engine.url.get_backend_name() != "sqlite" or engine.url.database in (None, "", ":memory:"):
        return

    @event.listens_for(engine, "connect")
    def set_pragmas(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def seed_sites():
    """Load the EIA-860M site list once (rebuild it with scripts/build_sites.py)."""
    if Site.query.first():
        return
    with SITES_CSV.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            db.session.add(Site(
                id=row["id"],
                eia_plant_id=int(row["eia_plant_id"]),
                name=row["name"],
                eia_name=row["eia_name"],
                state=row["state"],
                county=row["county"],
                lat=float(row["lat"]),
                lng=float(row["lng"]),
                utility=row["utility"],
                plant_type=row["plant_type"],
                capacity_mw=float(row["capacity_mw"]),
                timezone=row["timezone"],
                waterway=row["waterway"] or None,
            ))
    log.info("Seeded job sites from %s", SITES_CSV.name)


def seed_settings():
    for key, value in DEFAULTS.items():
        if not db.session.get(Setting, key):
            db.session.add(Setting(key=key, value=value))


def seed_demo_users(password):
    """Two demo accounts, one per role, both at Turkey Point. Only when SEED_DEMO_USERS is on (development)."""
    site_id = DEMO_SITE if db.session.get(Site, DEMO_SITE) else None
    if User.query.first():
        # Databases from before designated sites: give the demo accounts one.
        for user in User.query.filter(User.username.in_(["supervisor", "crew"]), User.site_id.is_(None)):
            user.site_id = site_id
        return
    for username, role in (("supervisor", "supervisor"), ("crew", "crew")):
        user = User(username=username, email=f"{username}@planit.dev", role=role, site_id=site_id)
        user.set_password(password)
        db.session.add(user)
    log.info("Seeded demo accounts 'supervisor' and 'crew'")


def upgrade_schema():
    """Add columns that newer code expects to databases created before them (create_all only adds tables)."""
    if "site_id" not in {column["name"] for column in inspect(db.engine).get_columns("users")}:
        with db.engine.begin() as connection:
            connection.execute(text("ALTER TABLE users ADD COLUMN site_id VARCHAR(80) REFERENCES sites(id) ON DELETE SET NULL"))
        log.info("Added users.site_id (designated site) to the existing database")


def init_db(app):
    enable_sqlite_wal(db.engine)
    db.create_all()
    upgrade_schema()
    seed_sites()
    seed_settings()
    if app.config["SEED_DEMO_USERS"]:
        seed_demo_users(app.config["DEMO_PASSWORD"])
    db.session.commit()

"""Backend configuration, read from environment variables (or backend/.env).

Every setting has a working development default. In production set at least
APP_ENV=production and SECRET_KEY. See backend/.env.example for the full list.
"""
import os
import secrets
from datetime import timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent


def load_env_file(path=BACKEND_DIR / ".env"):
    """Tiny .env loader (KEY=VALUE per line). Real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()


def env(name, default=""):
    return os.environ.get(name, default)


def env_bool(name, default):
    value = os.environ.get(name)
    return default if value is None else value.strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default):
    return [item.strip() for item in env(name, default).split(",") if item.strip()]


class Config:
    APP_ENV = env("APP_ENV", "development")
    # Without SECRET_KEY a random key is used, so sessions reset on every restart.
    SECRET_KEY = env("SECRET_KEY") or secrets.token_hex(32)

    # Database: SQLite file by default (backend/instance/planit.db).
    SQLALCHEMY_DATABASE_URI = env("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'instance' / 'planit.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"connect_args": {"timeout": 30}} if SQLALCHEMY_DATABASE_URI.startswith("sqlite") else {}

    # Session cookie (Flask-Login). SameSite=Lax blocks cross-site form posts.
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", APP_ENV == "production")
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE

    # Frontend: built files served by Flask, and extra origins allowed to call the API.
    FRONTEND_DIST = Path(env("FRONTEND_DIST", str(BACKEND_DIR.parent / "frontend" / "dist")))
    FRONTEND_ORIGINS = env_list("FRONTEND_ORIGINS", "http://localhost:5173")

    # Crew hazard report photos.
    UPLOAD_FOLDER = Path(env("UPLOAD_FOLDER", str(BACKEND_DIR / "uploads")))
    MAX_CONTENT_LENGTH = int(env("MAX_UPLOAD_MB", "10")) * 1024 * 1024

    # Background data refresh jobs (weather, NWS, rivers, fires, wildlife, lightning, briefings).
    ENABLE_JOBS = env_bool("ENABLE_JOBS", True)
    WEATHER_REFRESH_MINUTES = int(env("WEATHER_REFRESH_MINUTES", "60"))
    LIGHTNING_SOURCE = env("LIGHTNING_SOURCE", "glm")  # "glm" (NOAA GOES satellites) or "off"
    GLM_SATELLITES = env_list("GLM_SATELLITES", "goes19")
    LIGHTNING_POLL_SECONDS = int(env("LIGHTNING_POLL_SECONDS", "60"))

    # Demo helpers: seeded accounts and the supervisor-only "simulate strike" button.
    DEMO_TOOLS = env_bool("DEMO_TOOLS", APP_ENV == "development")
    SEED_DEMO_USERS = env_bool("SEED_DEMO_USERS", APP_ENV == "development")
    DEMO_PASSWORD = env("DEMO_PASSWORD", "planit-demo")

    # External data sources. CONTACT_EMAIL goes in the User-Agent (NWS asks for one).
    CONTACT_EMAIL = env("CONTACT_EMAIL")
    OPEN_METEO_API_KEY = env("OPEN_METEO_API_KEY")  # optional, for Open-Meteo's commercial API

    # AI assistant (POST /api/chat): Gemini or Claude, whichever key is set. Keys stay on the server.
    # With both keys, Claude answers unless ASSISTANT_PROVIDER=gemini.
    ASSISTANT_PROVIDER = env("ASSISTANT_PROVIDER", "auto")  # auto | claude | gemini
    GEMINI_API_KEY = env("GEMINI_API_KEY")
    GEMINI_MODEL = env("GEMINI_MODEL", "gemini-3.8-flash")
    ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY")
    CLAUDE_MODEL = env("CLAUDE_MODEL", "claude-opus-5-5")
    CHAT_RATE_LIMIT_PER_MINUTE = int(env("CHAT_RATE_LIMIT_PER_MINUTE", "20"))

    # Outbound notifications. Unset = messages are recorded in the outbox only.
    SMTP_HOST = env("SMTP_HOST")
    SMTP_PORT = int(env("SMTP_PORT", "587"))
    SMTP_USER = env("SMTP_USER")
    SMTP_PASSWORD = env("SMTP_PASSWORD")
    SMTP_FROM = env("SMTP_FROM", "planit-control@localhost")
    TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN")
    TWILIO_FROM = env("TWILIO_FROM")


class TestConfig(Config):
    """Used by the pytest suite: in-memory database, no background jobs, no network."""
    TESTING = True
    APP_ENV = "testing"
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_SECURE = False
    ENABLE_JOBS = False
    LIGHTNING_SOURCE = "off"
    DEMO_TOOLS = True
    SEED_DEMO_USERS = True
    ASSISTANT_PROVIDER = "auto"
    GEMINI_API_KEY = ""
    ANTHROPIC_API_KEY = ""
    SMTP_HOST = ""
    TWILIO_ACCOUNT_SID = ""

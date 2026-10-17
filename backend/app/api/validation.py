"""Input validation shared by the endpoints."""
import re
from zoneinfo import ZoneInfo

from ..extensions import db
from ..models import ROLES, Site

USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,64}$")
EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
PHONE = re.compile(r"^\+[1-9][0-9]{7,14}$")  # E.164, e.g. +13055550123
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def user_problem(username=None, email=None, password=None, role=None, phone=None):
    """First problem with the given user fields (None if all present fields are valid)."""
    if username is not None and not USERNAME.match(username):
        return "Username must be 3-64 letters, digits, dots, dashes or underscores."
    if email is not None and (len(email) > 120 or not EMAIL.match(email)):
        return "Enter a valid email address."
    if password is not None and len(password) < 8:
        return "Password must be at least 8 characters."
    if role is not None and role not in ROLES:
        return f"Role must be one of: {', '.join(ROLES)}."
    if phone not in (None, "") and not PHONE.match(phone):
        return "Phone must be in international format, e.g. +13055550123."
    return None


def site_choice(value, required):
    """(site id or None, problem or None) for a designated site, which must be an active job site."""
    site_id = value.strip() if isinstance(value, str) else ""
    if not site_id:
        return None, "Choose the site you work at." if required else None
    site = db.session.get(Site, site_id) if SLUG.match(site_id) else None
    if not site or not site.active:
        return None, "Choose one of the active job sites."
    return site_id, None


def valid_timezone(name):
    try:
        ZoneInfo(name)
        return True
    except Exception:
        return False


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def number(value, low, high, name):
    """Float within [low, high] or ValueError with a readable message."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number.") from None
    if not low <= result <= high:
        raise ValueError(f"{name} must be between {low:g} and {high:g}.")
    return result

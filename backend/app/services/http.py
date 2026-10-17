"""Shared HTTP helper for calls to public data sources."""
import math
import threading

import requests
from flask import current_app

_local = threading.local()
TIMEOUT_SECONDS = 30


def session():
    """One requests.Session per thread, identifying the app (NWS asks for a contact in the User-Agent)."""
    if not hasattr(_local, "session"):
        contact = current_app.config.get("CONTACT_EMAIL") or "contact not set"
        _local.session = requests.Session()
        _local.session.headers["User-Agent"] = f"PlanIT-Control/1.0 ({contact})"
    return _local.session


def get(url, **kwargs):
    kwargs.setdefault("timeout", TIMEOUT_SECONDS)
    response = session().get(url, **kwargs)
    return response


def haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance in miles."""
    lat1, lon1, lat2, lon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    a = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(a))

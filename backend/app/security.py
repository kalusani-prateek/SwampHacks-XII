"""Request helpers: JSON error responses, role checks and a small rate limiter."""
import time
from collections import defaultdict, deque
from functools import wraps
from threading import Lock

from flask import jsonify
from flask_login import current_user


def error(message, status):
    """JSON error in the API's standard shape: {"message": ...}."""
    return jsonify(message=message), status


def supervisor_required(view):
    """Allow only signed-in supervisors (they hold all management privileges)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return error("Authentication required", 401)
        if not current_user.is_supervisor:
            return error("Supervisor privileges required", 403)
        return view(*args, **kwargs)
    return wrapper


class RateLimiter:
    """In-memory sliding-window limiter (per process), e.g. 20 chat messages a minute per user."""

    def __init__(self):
        self._hits = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key, limit, window_seconds=60):
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True


limiter = RateLimiter()

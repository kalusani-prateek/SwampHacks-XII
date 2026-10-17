"""Web Push: notifications on phones and computers, even when the app is closed.

Each browser that turns notifications on registers a subscription (an address at
its push service plus encryption keys, table push_subscriptions). To notify
someone we encrypt a small JSON message for each of their devices, sign it with
our VAPID key and post it to that address; the browser's service worker
(frontend/public/sw.js) shows it. Subscriptions the push service reports as gone
(404/410) are deleted. Every attempt is recorded in the notifications table
(channel "push"), next to email and SMS.

Crew are notified about their designated site: tomorrow's briefing, the site
turning NO-GO, and new hazard reports there.
"""
import json
import logging
import threading
from base64 import urlsafe_b64encode
from datetime import timedelta

from cryptography.hazmat.primitives import serialization
from flask import current_app
from py_vapid import Vapid
from pywebpush import WebPushException, webpush

from ..extensions import db
from ..models import Notification, PushSubscription, User, utcnow

log = logging.getLogger(__name__)

NO_GO_COOLDOWN = timedelta(hours=1)  # at most one NO-GO notification per site per hour
_keys = {}  # key file -> Vapid
_keys_lock = threading.Lock()
_last_no_go = {}  # site id -> when its NO-GO notification went out


def signing_key():
    """The server's VAPID key, created on first use."""
    path = current_app.config["VAPID_PRIVATE_KEY_FILE"]
    with _keys_lock:
        if path not in _keys:
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                key = Vapid()
                key.generate_keys()
                key.save_key(str(path))
                log.info("Created the Web Push signing key in %s", path)
            _keys[path] = Vapid.from_file(str(path))
        return _keys[path]


def public_key():
    """The public half, base64url-encoded, which browsers need to subscribe."""
    raw = signing_key().public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return urlsafe_b64encode(raw).rstrip(b"=").decode()


def _send(subscription_info, payload, key, claims):
    """Encrypt and post one message (replaced in tests)."""
    webpush(subscription_info, data=payload, vapid_private_key=key, vapid_claims=claims, ttl=12 * 3600, timeout=10)


def send_to_users(users, title, body, url="/", tag=None):
    """Notify every device of these users. Returns how many devices were targeted."""
    ids = [u.id for u in users]
    subs = PushSubscription.query.filter(PushSubscription.user_id.in_(ids)).all() if ids else []
    if not subs:
        return 0
    payload = json.dumps({"title": title, "body": body, "url": url, "tag": tag})
    deliveries = [(s.id, {"endpoint": s.endpoint, "keys": {"p256dh": s.p256dh, "auth": s.auth}}, s.user.username)
                  for s in subs]
    app, key = current_app._get_current_object(), signing_key()
    if app.config["PUSH_IN_BACKGROUND"]:
        threading.Thread(target=_deliver, args=(app, deliveries, payload, key, title, body), daemon=True).start()
    else:
        _deliver(app, deliveries, payload, key, title, body)
    return len(deliveries)


def _deliver(app, deliveries, payload, key, title, body):
    gone, records = [], []
    for sub_id, info, username in deliveries:
        status, error = "sent", None
        try:
            _send(info, payload, key, {"sub": app.config["VAPID_SUBJECT"]})
        except WebPushException as exc:
            code = getattr(exc.response, "status_code", None)
            if code in (404, 410):  # the browser unsubscribed or the subscription expired
                gone.append(sub_id)
            status, error = "failed", f"{code or ''} {exc}".strip()[:500]
        except Exception as exc:  # network trouble: keep the subscription, record the failure
            status, error = "failed", str(exc)[:500]
        records.append(Notification(channel="push", recipient=username, subject=title, body=body,
                                    status=status, error=error))
    from .ingest import WRITE_LOCK  # one database writer at a time
    with app.app_context(), WRITE_LOCK:
        if gone:
            PushSubscription.query.filter(PushSubscription.id.in_(gone)).delete(synchronize_session=False)
        db.session.add_all(records)
        db.session.commit()


def notify_site(site_id, title, body, url, tag, exclude_user_id=None):
    """Notify everyone whose designated site this is (except, e.g., the person who caused it)."""
    query = User.query.filter(User.site_id == site_id)
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    try:
        return send_to_users(query.all(), title, body, url, tag)
    except Exception:  # notifications must never break the action that triggered them
        log.exception("Couldn't send push notifications for site %s", site_id)
        return 0


def notify_no_go(site):
    """A site just turned NO-GO: tell the people who work there (once an hour at most)."""
    now = utcnow()
    if site.id in _last_no_go and now - _last_no_go[site.id] < NO_GO_COOLDOWN:
        return 0
    _last_no_go[site.id] = now
    reason = (site.drivers or ["Conditions are dangerous right now."])[0]
    return notify_site(site.id, f"⛔ {site.name} is NO-GO", f"Hazard index {site.hazard_index:.1f}/10. {reason}",
                       url=f"/sites/{site.id}", tag=f"nogo-{site.id}")

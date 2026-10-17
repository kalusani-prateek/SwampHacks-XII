"""Phone and desktop notifications (Web Push): turn them on or off for this device, or send a test."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import PushSubscription
from ..security import error, limiter
from ..services import push

bp = Blueprint("push", __name__)


@bp.get("/push/key")
def public_key():
    """The server's public key, which the browser needs to subscribe."""
    return {"publicKey": push.public_key()}


@bp.post("/push/subscriptions")
@login_required
def subscribe():
    """Body: the browser's PushSubscription JSON, { endpoint, keys: { p256dh, auth } }."""
    data = request.get_json(silent=True) or {}
    endpoint, keys = data.get("endpoint"), data.get("keys") or {}
    p256dh, auth = keys.get("p256dh"), keys.get("auth")
    if not (isinstance(endpoint, str) and endpoint.startswith("https://") and len(endpoint) <= 1000):
        return error("A push subscription needs an https endpoint", 400)
    if not all(isinstance(value, str) and 16 <= len(value) <= 200 for value in (p256dh, auth)):
        return error("A push subscription needs its p256dh and auth keys", 400)
    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if sub:  # same browser: keep one row, now for whoever is signed in
        sub.user_id, sub.p256dh, sub.auth = current_user.id, p256dh, auth
    else:
        db.session.add(PushSubscription(user_id=current_user.id, endpoint=endpoint, p256dh=p256dh, auth=auth))
    db.session.commit()
    return {"message": "Notifications are on for this device"}, 201


@bp.delete("/push/subscriptions")
@login_required
def unsubscribe():
    """Body: { endpoint }."""
    endpoint = (request.get_json(silent=True) or {}).get("endpoint")
    PushSubscription.query.filter_by(endpoint=endpoint, user_id=current_user.id).delete()
    db.session.commit()
    return {"message": "Notifications are off for this device"}


@bp.post("/push/test")
@login_required
def test():
    """Send a test notification to every device of the signed-in user."""
    if not limiter.allow(f"push-test:{current_user.id}", limit=5):
        return error("Too many test notifications. Wait a minute and try again.", 429)
    devices = push.send_to_users([current_user], "PlanIT test notification",
                                 "Notifications are working on this device.", url="/account", tag="test")
    if not devices:
        return error("None of your devices has notifications turned on yet", 404)
    return {"message": f"Sent to {devices} device{'s' if devices != 1 else ''}", "devices": devices}

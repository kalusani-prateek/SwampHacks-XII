"""Alerts: list, acknowledge, and a live Server-Sent Events stream."""
import json
import queue

from flask import Blueprint, Response, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Alert, AlertAck
from ..security import error
from ..services.events import bus

bp = Blueprint("alerts", __name__)
SEVERITY_ORDER = {"stop-work": 0, "warning": 1, "info": 2}


@bp.get("/alerts")
@login_required
def list_alerts():
    query = Alert.query
    if request.args.get("active") == "true":
        query = query.filter_by(active=True)
    if request.args.get("siteId"):
        query = query.filter_by(site_id=request.args["siteId"])
    alerts = query.order_by(Alert.created_at.desc()).limit(500).all()
    alerts.sort(key=lambda a: SEVERITY_ORDER.get(a.severity, 9))  # stable: newest first within a severity
    return {"alerts": [a.to_dict(current_user) for a in alerts]}


@bp.post("/alerts/<int:alert_id>/ack")
@login_required
def acknowledge(alert_id):
    alert = db.session.get(Alert, alert_id)
    if not alert:
        return error("Alert not found", 404)
    if not AlertAck.query.filter_by(alert_id=alert.id, user_id=current_user.id).first():
        db.session.add(AlertAck(alert_id=alert.id, user_id=current_user.id))
        db.session.commit()
    return {"alert": alert.to_dict(current_user)}


@bp.get("/alerts/stream")
@login_required
def stream():
    """Push a message to the browser whenever an alert, report or briefing is created."""
    subscription = bus.subscribe()

    def events():
        try:
            yield "retry: 5000\n\n"
            while True:
                try:
                    event = subscription.get(timeout=20)
                except queue.Empty:
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            bus.unsubscribe(subscription)

    return Response(events(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

"""Recent outbound notifications (the outbox), for supervisors."""
from flask import Blueprint, request

from ..models import Notification
from ..security import supervisor_required

bp = Blueprint("notifications", __name__)


@bp.get("/notifications")
@supervisor_required
def list_notifications():
    limit = min(max(request.args.get("limit", 20, type=int), 1), 200)
    rows = Notification.query.order_by(Notification.created_at.desc()).limit(limit)
    return {"notifications": [n.to_dict() for n in rows]}

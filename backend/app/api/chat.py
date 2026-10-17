"""AI assistant endpoint."""
from flask import Blueprint, current_app, request
from flask_login import current_user, login_required

from ..security import error, limiter
from ..services import assistant

bp = Blueprint("chat", __name__)


@bp.post("/chat")
@login_required
def chat():
    if not limiter.allow(f"chat:{current_user.id}", current_app.config["CHAT_RATE_LIMIT_PER_MINUTE"]):
        return error("You're sending messages too quickly. Wait a minute and try again.", 429)
    try:
        messages, site_id = assistant.validate(request.get_json(silent=True) or {})
    except ValueError as exc:
        return error(str(exc), 400)
    try:
        content = assistant.reply(messages, current_user, site_id)
    except assistant.AssistantError as exc:
        return error(exc.message, exc.status)
    return {"reply": {"role": "assistant", "content": content}}

"""AI assistant: answers crew and supervisor questions with Claude, grounded in live site data.

The API key stays on the server (ANTHROPIC_API_KEY). Each request sends the
fixed instructions plus a JSON snapshot of the data the user can see.
"""
import json
import re

import anthropic
from flask import current_app

from ..extensions import db
from ..models import Alert, Site
from ..settings_store import get_setting
from . import ingest
from .briefings import build_briefing
from .hazards import level

MAX_MESSAGES = 20
MAX_CHARS = 2000
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

SYSTEM_PROMPT = """You are PlanIT Assistant, a safety assistant for utility field crews and supervisors at power plant job sites.
- Answer from the live site data below. If something isn't in it, say you don't know.
- Never say it is safe to work while a stop-work alert or lightning countdown is active.
- For injuries or emergencies, tell them to call 911 first, then their supervisor.
- Reply in plain text: short sentences and "•" bullets, no markdown. People read this on phones in the field."""


class AssistantError(Exception):
    def __init__(self, message, status):
        super().__init__(message)
        self.message, self.status = message, status


def validate(payload):
    """Return (messages, site_id) or raise ValueError with a user-facing message."""
    messages = payload.get("messages")
    if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
        raise ValueError(f"Send between 1 and {MAX_MESSAGES} messages.")
    cleaned = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            raise ValueError("Each message needs a role of 'user' or 'assistant'.")
        content = message.get("content")
        if not isinstance(content, str) or not 1 <= len(content.strip()) <= MAX_CHARS:
            raise ValueError(f"Each message must be 1-{MAX_CHARS} characters.")
        cleaned.append({"role": message["role"], "content": content.strip()})
    if cleaned[0]["role"] != "user":
        raise ValueError("The conversation must start with a user message.")
    site_id = payload.get("siteId")
    if site_id is not None and (not isinstance(site_id, str) or not SLUG.match(site_id)):
        raise ValueError("Invalid siteId.")
    return cleaned, site_id


def site_summary(site):
    band = level(site.hazard_index or 0)
    return {
        "name": site.name, "state": site.state, "waterway": site.waterway,
        "hazardIndex": round(site.hazard_index or 0, 1), "decision": band["decision"],
        "drivers": site.drivers or [],
    }


def build_context(user, site_id):
    """The data the assistant may use: riskiest sites, rules, and the site on screen."""
    rules = get_setting("alert_rules")
    sites = Site.query.filter_by(active=True).all()
    ranked = sorted(sites, key=lambda s: s.hazard_index or 0, reverse=True)[:5]
    context = {
        "userRole": user.role,
        "alertRules": rules,
        "riskiestSites": [site_summary(s) for s in ranked],
    }
    site = db.session.get(Site, site_id) if site_id else None
    if site and site.active:
        context["currentSite"] = {
            **site_summary(site),
            "hazards": site.hazards or {},
            "conditions": site.conditions or {},
            "activeAlerts": [
                {"title": a.title, "message": a.message, "severity": a.severity}
                for a in Alert.query.filter_by(site_id=site.id, active=True)
            ],
            "lightning": ingest.lightning_status(site.id, rules),
            "tomorrow": build_briefing(site),
        }
    return context


def reply(messages, user, site_id):
    """Ask Claude. Raises AssistantError with an HTTP status for the API to return."""
    api_key = current_app.config["ANTHROPIC_API_KEY"]
    if not api_key:
        raise AssistantError("The AI assistant isn't set up on this server yet (ANTHROPIC_API_KEY is missing).", 503)
    client = anthropic.Anthropic(api_key=api_key)
    system = f"{SYSTEM_PROMPT}\n\n<site_data>\n{json.dumps(build_context(user, site_id), default=str)}\n</site_data>"
    try:
        response = client.beta.messages.create(
            model=current_app.config["CLAUDE_MODEL"],
            max_tokens=16000,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # if a safety check declines, re-run on Anthropic's fallback model
            system=system,
            messages=messages,
        )
    except anthropic.RateLimitError as exc:
        raise AssistantError("The assistant is busy. Try again in a minute.", 503) from exc
    except anthropic.APIStatusError as exc:
        raise AssistantError("The assistant is unavailable right now.", 502) from exc
    except anthropic.APIConnectionError as exc:
        raise AssistantError("Can't reach the assistant service.", 502) from exc

    if response.stop_reason == "refusal":
        return "I can't help with that one. Please ask your supervisor."
    # The reply can include thinking blocks; keep only the text.
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return text or "Sorry, I don't have an answer for that."

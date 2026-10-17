"""AI assistant: answers crew and supervisor questions with Gemini or Claude, grounded in live site data.

The API key stays on the server (GEMINI_API_KEY or ANTHROPIC_API_KEY). Each
request sends the fixed instructions plus a JSON snapshot of the data the user
can see.
"""
import json
import logging
import re

import anthropic
import requests
from flask import current_app

from ..extensions import db
from ..models import Alert, Site
from ..settings_store import get_setting
from . import ingest
from .briefings import build_briefing
from .hazards import level

log = logging.getLogger(__name__)

MAX_MESSAGES = 20
MAX_CHARS = 2000
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_BLOCKED = {"SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "SPII"}  # finish reasons meaning "declined"
REFUSAL = "I can't help with that one. Please ask your supervisor."

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


def provider(cfg):
    """Which service answers: "claude", "gemini", or None when its key isn't set."""
    keys = {"claude": cfg["ANTHROPIC_API_KEY"], "gemini": cfg["GEMINI_API_KEY"]}
    choice = cfg["ASSISTANT_PROVIDER"]
    if choice in keys:
        return choice if keys[choice] else None
    return next((name for name, key in keys.items() if key), None)  # auto: Claude first, then Gemini


def reply(messages, user, site_id):
    """Ask the configured AI service. Raises AssistantError with an HTTP status for the API to return."""
    name = provider(current_app.config)
    if name is None:
        raise AssistantError(
            "The AI assistant isn't set up on this server yet (set GEMINI_API_KEY or ANTHROPIC_API_KEY).", 503)
    system = f"{SYSTEM_PROMPT}\n\n<site_data>\n{json.dumps(build_context(user, site_id), default=str)}\n</site_data>"
    text = ask_claude(system, messages) if name == "claude" else ask_gemini(system, messages)
    return text or "Sorry, I don't have an answer for that."


def ask_claude(system, messages):
    client = anthropic.Anthropic(api_key=current_app.config["ANTHROPIC_API_KEY"])
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
        log.warning("Claude returned %s: %s", exc.status_code, exc.message)
        raise AssistantError("The assistant is unavailable right now.", 502) from exc
    except anthropic.APIConnectionError as exc:
        raise AssistantError("Can't reach the assistant service.", 502) from exc

    if response.stop_reason == "refusal":
        return REFUSAL
    # The reply can include thinking blocks; keep only the text.
    return "".join(block.text for block in response.content if block.type == "text").strip()


def ask_gemini(system, messages):
    """Gemini's REST API (generateContent). The key goes in a header, never in the URL."""
    cfg = current_app.config
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        # Gemini calls the assistant's turns "model".
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ],
        "generationConfig": {"maxOutputTokens": 8192},  # room for the model's thinking plus a short answer
    }
    try:
        response = requests.post(GEMINI_URL.format(model=cfg["GEMINI_MODEL"]), json=body,
                                 headers={"x-goog-api-key": cfg["GEMINI_API_KEY"]}, timeout=60)
    except requests.RequestException as exc:
        raise AssistantError("Can't reach the assistant service.", 502) from exc
    if response.status_code == 429:
        raise AssistantError("The assistant is busy. Try again in a minute.", 503)
    if not response.ok:
        log.warning("Gemini returned %s: %s", response.status_code, response.text[:500])
        raise AssistantError("The assistant is unavailable right now.", 502)

    data = response.json()
    candidate = (data.get("candidates") or [{}])[0]
    # Thought summaries (if any) are marked "thought"; keep only the answer.
    parts = candidate.get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts if not part.get("thought")).strip()
    if not text and (data.get("promptFeedback", {}).get("blockReason") or candidate.get("finishReason") in GEMINI_BLOCKED):
        return REFUSAL
    return text

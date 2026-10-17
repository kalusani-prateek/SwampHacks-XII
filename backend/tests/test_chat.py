"""AI assistant endpoint, with Claude replaced by a stand-in client (no network, no cost)."""
from types import SimpleNamespace

import pytest

from app.services import assistant


class FakeClaude:
    """Records the request and returns a canned reply shaped like the Anthropic SDK's."""
    calls = []
    reply = SimpleNamespace(stop_reason="end_turn", content=[
        SimpleNamespace(type="thinking", thinking=""),
        SimpleNamespace(type="text", text="• Stop work until the all-clear."),
    ])

    def __init__(self, api_key):
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        FakeClaude.calls.append(kwargs)
        return FakeClaude.reply


@pytest.fixture
def claude(app, monkeypatch):
    app.config["ANTHROPIC_API_KEY"] = "test-key"
    FakeClaude.calls = []
    monkeypatch.setattr(assistant.anthropic, "Anthropic", FakeClaude)
    return FakeClaude


def ask(client, text="Is it safe?", site_id="turkey-point"):
    return client.post("/api/chat", json={"messages": [{"role": "user", "content": text}], "siteId": site_id})


def test_without_an_api_key_the_assistant_says_so(crew):
    response = ask(crew)
    assert response.status_code == 503
    assert "ANTHROPIC_API_KEY" in response.get_json()["message"]


def test_reply_uses_live_site_data_and_skips_thinking_blocks(crew, claude):
    response = ask(crew)
    assert response.status_code == 200
    assert response.get_json()["reply"] == {"role": "assistant", "content": "• Stop work until the all-clear."}
    call = claude.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default" and "server-side-fallback-2026-07-01" in call["betas"]
    assert "<site_data>" in call["system"] and "Turkey Point" in call["system"]


def test_refusals_get_a_polite_answer(crew, claude):
    claude.reply = SimpleNamespace(stop_reason="refusal", content=[])
    try:
        assert "ask your supervisor" in ask(crew).get_json()["reply"]["content"]
    finally:
        claude.reply = FakeClaude.reply.__class__(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="ok")])


@pytest.mark.parametrize("payload", [
    {"messages": []},
    {"messages": [{"role": "assistant", "content": "hi"}]},
    {"messages": [{"role": "user", "content": "x" * 2001}]},
    {"messages": [{"role": "system", "content": "hi"}]},
    {"messages": [{"role": "user", "content": "hi"}], "siteId": "../etc"},
])
def test_invalid_conversations_are_rejected(crew, claude, payload):
    assert crew.post("/api/chat", json=payload).status_code == 400


def test_rate_limit(app, crew, claude):
    app.config["CHAT_RATE_LIMIT_PER_MINUTE"] = 2
    assert ask(crew).status_code == 200
    assert ask(crew).status_code == 200
    assert ask(crew).status_code == 429

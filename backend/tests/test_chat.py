"""AI assistant endpoint, with Claude and Gemini replaced by stand-ins (no network, no cost)."""
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


class FakeGemini:
    """Stands in for requests.post to Gemini's REST API; records each request."""
    calls = []
    status = 200
    body = {"candidates": [{"finishReason": "STOP", "content": {"role": "model", "parts": [
        {"text": "Weighing the lightning rule...", "thought": True},
        {"text": "• Stop work until the all-clear."},
    ]}}]}

    @classmethod
    def post(cls, url, json, headers, timeout):
        cls.calls.append({"url": url, "json": json, "headers": headers})
        return SimpleNamespace(status_code=cls.status, ok=cls.status < 400, text=str(cls.body), json=lambda: cls.body)


@pytest.fixture
def gemini(app, monkeypatch):
    app.config["GEMINI_API_KEY"] = "test-gemini-key"
    monkeypatch.setattr(FakeGemini, "calls", [])
    monkeypatch.setattr(FakeGemini, "status", 200)
    monkeypatch.setattr(FakeGemini, "body", FakeGemini.body)
    monkeypatch.setattr(assistant.requests, "post", FakeGemini.post)
    return FakeGemini


def test_without_an_api_key_the_assistant_says_so(crew):
    response = ask(crew)
    assert response.status_code == 503
    message = response.get_json()["message"]
    assert "GEMINI_API_KEY" in message and "ANTHROPIC_API_KEY" in message


def test_gemini_reply_uses_live_site_data_and_skips_thoughts(crew, gemini):
    response = ask(crew)
    assert response.status_code == 200
    assert response.get_json()["reply"] == {"role": "assistant", "content": "• Stop work until the all-clear."}
    call = gemini.calls[0]
    assert call["url"].endswith("/models/gemini-3.8-flash:generateContent")
    assert call["headers"] == {"x-goog-api-key": "test-gemini-key"} and "test-gemini-key" not in call["url"]
    system = call["json"]["systemInstruction"]["parts"][0]["text"]
    assert "<site_data>" in system and "Turkey Point" in system


def test_gemini_gets_the_conversation_with_its_role_names(crew, gemini):
    conversation = [
        {"role": "user", "content": "Is it safe?"},
        {"role": "assistant", "content": "Not right now."},
        {"role": "user", "content": "Why?"},
    ]
    assert crew.post("/api/chat", json={"messages": conversation}).status_code == 200
    contents = gemini.calls[0]["json"]["contents"]
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    assert contents[1]["parts"] == [{"text": "Not right now."}]


def test_gemini_blocked_prompts_get_a_polite_answer(crew, gemini):
    gemini.body = {"promptFeedback": {"blockReason": "SAFETY"}}
    assert "ask your supervisor" in ask(crew).get_json()["reply"]["content"]


@pytest.mark.parametrize("status, expected", [(429, 503), (400, 502), (500, 502)])
def test_gemini_errors_become_friendly_messages(crew, gemini, status, expected):
    gemini.status = status
    gemini.body = {"error": {"message": "API key not valid."}}
    response = ask(crew)
    assert response.status_code == expected
    assert "API key" not in response.get_json()["message"]  # details go to the server log, not the user


def test_with_both_keys_claude_answers_unless_gemini_is_chosen(app, client, crew, claude, gemini):
    assert client.get("/api/meta").get_json()["assistant"] is True
    ask(crew)
    assert len(claude.calls) == 1 and not gemini.calls
    app.config["ASSISTANT_PROVIDER"] = "gemini"
    ask(crew)
    assert len(gemini.calls) == 1 and len(claude.calls) == 1


def test_chosen_provider_without_its_key_is_off(app, client, gemini):
    app.config["ASSISTANT_PROVIDER"] = "claude"
    assert client.get("/api/meta").get_json()["assistant"] is False


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

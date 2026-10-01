import json
from pathlib import Path

import pytest

from nerfwatch import providers

FIX = json.loads((Path(__file__).parent / "fixtures" / "responses.json").read_text())


@pytest.fixture(autouse=True)
def keys(monkeypatch):
    for v in ("OPENAI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(v, "test-key")


@pytest.mark.parametrize("spec", list(FIX))
def test_parse_recorded_response(spec):
    assert providers.parse_response(spec, FIX[spec]) == "391"


@pytest.mark.parametrize("spec", list(FIX))
def test_build_request_shape(spec):
    url, body, headers = providers.build_request(spec, "What is 17*23?", 0.0)
    assert url.startswith("http")
    assert json.dumps(body)  # serialisable
    if spec.startswith("ollama/"):
        assert body["think"] is False and body["options"]["temperature"] == 0.0
    elif spec.startswith("anthropic/"):
        assert headers["x-api-key"] == "test-key" and body["system"]
    elif spec.startswith("gemini/"):
        assert headers["x-goog-api-key"] == "test-key"
    else:
        assert headers["Authorization"] == "Bearer test-key"


def test_missing_key_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        providers.build_request("openai/gpt-4o-mini", "hi", 0.0)


def test_complete_uses_post(monkeypatch):
    seen = {}

    def fake_post(url, body, headers, timeout=120):
        seen.update(url=url, body=body)
        return FIX["openai/gpt-4o-mini"]

    monkeypatch.setattr(providers, "_post", fake_post)
    assert providers.complete("openai/gpt-4o-mini", "q", 0.5) == "391"
    assert seen["body"]["temperature"] == 0.5


def test_unknown_provider():
    with pytest.raises(ValueError):
        providers.build_request("nope/x", "q", 0.0)

from __future__ import annotations

from autograde.llm.client import MockLLMProvider, get_default_provider


def test_default_provider_falls_back_to_mock(monkeypatch):
    monkeypatch.delenv("AUTOGRADE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    provider = get_default_provider()
    assert isinstance(provider, MockLLMProvider)

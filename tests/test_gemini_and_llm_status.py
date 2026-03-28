from __future__ import annotations

import json

from fastapi.testclient import TestClient

from autograde.api.app import app
from autograde.llm.client import GeminiProvider, MockLLMProvider, get_default_provider
from autograde.llm.schemas import LLMRequest


def test_gemini_provider_parses_generate_content_response(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'dummy-key')
    provider = GeminiProvider(model='gemini-3-flash-preview')

    def fake_post_json(url: str, payload: dict, headers=None):
        assert 'generateContent' in url
        return {
            'candidates': [
                {
                    'content': {
                        'parts': [
                            {
                                'text': json.dumps({
                                    'score': 0.81,
                                    'confidence': 0.77,
                                    'rationale': 'Looks good.',
                                    'evidence_refs': ['ev1'],
                                })
                            }
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr(provider, '_post_json', fake_post_json)
    raw = provider.complete_json(LLMRequest(
        evaluator_id='llm_subjective_reasoning',
        criterion_id='c1',
        prompt='Evaluate this.',
        evidence_refs=['ev1'],
    ))
    assert raw['provider'] == 'gemini'
    assert raw['model'] == 'gemini-3-flash-preview'
    assert raw['score'] == 0.81
    assert raw['confidence'] == 0.77


def test_auto_provider_prefers_gemini_when_key_present(monkeypatch):
    monkeypatch.setenv('GEMINI_API_KEY', 'dummy-key')
    monkeypatch.delenv('AUTOGRADE_LLM_PROVIDER', raising=False)
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)

    monkeypatch.setattr(GeminiProvider, 'is_available', lambda self: True)
    provider = get_default_provider()
    assert isinstance(provider, GeminiProvider)


def test_default_provider_can_still_fall_back_to_mock(monkeypatch):
    monkeypatch.delenv('AUTOGRADE_LLM_PROVIDER', raising=False)
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('OLLAMA_BASE_URL', raising=False)
    monkeypatch.setenv('AUTOGRADE_ALLOW_MOCK_LLM', '1')
    provider = get_default_provider()
    assert isinstance(provider, MockLLMProvider)


def test_llm_status_endpoint(monkeypatch):
    monkeypatch.setenv('AUTOGRADE_ALLOW_MOCK_LLM', '1')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.delenv('GOOGLE_API_KEY', raising=False)
    monkeypatch.delenv('OPENROUTER_API_KEY', raising=False)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.delenv('AUTOGRADE_LLM_PROVIDER', raising=False)
    client = TestClient(app)
    resp = client.get('/llm-status')
    assert resp.status_code == 200
    data = resp.json()
    assert 'provider_class' in data
    assert 'is_mock' in data
    assert 'is_live' in data

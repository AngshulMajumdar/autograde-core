from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Protocol

from autograde.llm.schemas import LLMClaimExtraction, LLMClaimItem, LLMEvaluation, LLMFeedback, LLMRequest

DEFAULT_TIMEOUT_SECONDS = 45


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _schema_text_for_request(request: LLMRequest) -> str:
    if request.evaluator_id == 'llm_rubric_induction':
        return '{"criteria": [{"name": "correctness", "description": "...", "weight": 0.4, "evaluators": ["subjective_reasoning"]}]}'
    if request.evaluator_id == 'llm_claim_extractor':
        return '{"claims": [{"claim_type": "...", "subject": "...", "value": "...", "confidence": <0-1>, "raw_text": "..."}], "rationale": "..."}'
    if request.evaluator_id == 'llm_feedback_generator':
        return '{"summary": "...", "strengths": ["..."], "weaknesses": ["..."], "suggestions": ["..."]}'
    return '{"score": <0-1>, "confidence": <0-1>, "rationale": "...", "evidence_refs": ["..."]}'


def _rubric_induction_stub() -> dict[str, Any]:
    criteria = [
        {'name': 'correctness', 'description': 'Assess whether the submission satisfies the core task requirements.', 'weight': 0.45, 'evaluators': ['subjective_reasoning']},
        {'name': 'explanation', 'description': 'Assess clarity and adequacy of the explanation or justification.', 'weight': 0.3, 'evaluators': ['argument_quality']},
        {'name': 'analysis', 'description': 'Assess analysis, interpretation, or discussion quality.', 'weight': 0.25, 'evaluators': ['result_analysis']},
    ]
    return {'criteria': criteria}


def _json_only_prompt(request: LLMRequest) -> str:
    return (
        'Return only valid JSON matching this schema: ' + _schema_text_for_request(request) + '\n\n'
        f'Evaluator: {request.evaluator_id}\n'
        f'Criterion: {request.criterion_id}\n'
        f'Evidence refs: {request.evidence_refs}\n\n'
        f'Prompt:\n{request.prompt}'
    )


class LLMProvider(Protocol):
    def complete_json(self, request: LLMRequest) -> dict[str, Any]: ...


class MockLLMProvider:
    """Deterministic offline provider so the package remains runnable without API access."""

    def complete_json(self, request: LLMRequest) -> dict[str, Any]:
        prompt = request.prompt.lower()
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_'-]*", prompt)
        unique = len(set(words))
        has_reasoning = any(tok in prompt for tok in ["because", "therefore", "however", "thus", "hence"])
        has_evidence = any(tok in prompt for tok in ["example", "evidence", "citation", "result", "figure", "table"])
        has_structure = any(tok in prompt for tok in ["introduction", "method", "conclusion", "thesis", "proof"])
        if request.evaluator_id == 'llm_rubric_induction':
            response = _rubric_induction_stub()
            response['provider'] = 'mock'
            return response
        if request.evaluator_id == 'llm_claim_extractor':
            claims = []
            for algo in ['dijkstra', 'bfs', 'dfs', 'bellman-ford', 'prim', 'kruskal']:
                if algo in prompt:
                    claims.append({'claim_type': 'algorithm_claim', 'subject': 'algorithm', 'value': algo, 'confidence': 0.72, 'raw_text': algo})
            for metric in ['accuracy', 'precision', 'recall', 'f1', 'loss', 'error', 'gain', 'cutoff']:
                m = re.search(rf"{metric}[^0-9]{{0,12}}(\d+(?:\.\d+)?)\s*(%?)", prompt)
                if m:
                    val = m.group(1) + ('%' if m.group(2) else '')
                    claims.append({'claim_type': 'metric_claim', 'subject': metric, 'value': val, 'confidence': 0.74, 'raw_text': m.group(0)})
            return {'claims': claims[:8], 'rationale': 'Offline mock claim extractor used lexical pattern extraction.', 'provider': 'mock'}
        if request.evaluator_id == 'llm_feedback_generator':
            strengths, weaknesses, suggestions = [], [], []
            if 'covered' in prompt or 'supported' in prompt:
                strengths.append('Core required components appear to be present in the evaluated evidence.')
            if 'contradicted' in prompt or 'unsupported' in prompt:
                weaknesses.append('Some claims are weakly supported or contradicted by other evidence in the submission.')
                suggestions.append('Align reported claims more tightly with code, tables, or design evidence.')
            if not strengths:
                strengths.append('The submission shows at least partial engagement with the assignment requirements.')
            if not weaknesses:
                weaknesses.append('Some criterion-level improvements are still needed for stronger evidence and clarity.')
            if not suggestions:
                suggestions.append('Strengthen justification and explicitly connect claims to evidence.')
            return {
                'summary': 'Structured feedback synthesized from criterion results and review signals.',
                'strengths': strengths[:3],
                'weaknesses': weaknesses[:3],
                'suggestions': suggestions[:3],
                'provider': 'mock',
            }
        base = 0.35 + min(unique / 250.0, 0.25)
        score = base + (0.15 if has_reasoning else 0.0) + (0.12 if has_evidence else 0.0) + (0.08 if has_structure else 0.0)
        confidence = 0.45 + min(len(words) / 1200.0, 0.25) + (0.08 if has_reasoning else 0.0)
        rationale = 'Offline mock LLM judged the evidence using reasoning markers, support markers, and structural cues.'
        return {
            'score': round(_clamp01(score), 4),
            'confidence': round(_clamp01(confidence), 4),
            'rationale': rationale,
            'evidence_refs': request.evidence_refs[:8],
            'provider': 'mock',
        }


class _HTTPJSONProvider:
    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _post_json(self, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> dict[str, Any]:
        data = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json', **(headers or {})}, method='POST')
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode('utf-8')
        return json.loads(body)

    def _get_json(self, url: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        request = urllib.request.Request(url, headers=headers or {}, method='GET')
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            body = response.read().decode('utf-8')
        return json.loads(body)


class OllamaProvider(_HTTPJSONProvider):
    def __init__(self, model: str = 'qwen2.5:7b-instruct', base_url: str | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        super().__init__(base_url or os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434'), timeout=timeout)
        self.model = model

    def is_available(self) -> bool:
        try:
            self._get_json(f'{self.base_url}/api/tags')
            return True
        except Exception:
            return False

    def complete_json(self, request: LLMRequest) -> dict[str, Any]:
        if request.evaluator_id == 'llm_rubric_induction':
            response = _rubric_induction_stub()
            response.update({'provider': 'ollama', 'model': self.model, 'note': 'rubric induction uses a bounded built-in scaffold'})
            return response
        payload = {'model': self.model, 'prompt': _json_only_prompt(request), 'stream': False, 'format': 'json', 'options': {'temperature': 0.1}}
        raw = self._post_json(f'{self.base_url}/api/generate', payload)
        response_text = raw.get('response', '{}')
        parsed = json.loads(response_text)
        parsed['provider'] = 'ollama'
        parsed['model'] = self.model
        return parsed


class GeminiProvider(_HTTPJSONProvider):
    def __init__(self, model: str = 'gemini-3-flash-preview', base_url: str = 'https://generativelanguage.googleapis.com/v1beta', api_key: str | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        super().__init__(base_url, timeout=timeout)
        self.model = model
        self.api_key = api_key or os.getenv('GEMINI_API_KEY', '') or os.getenv('GOOGLE_API_KEY', '')
        if not self.api_key:
            raise RuntimeError('GEMINI_API_KEY not configured')

    def is_available(self) -> bool:
        try:
            self._get_json(f'{self.base_url}/models/{self.model}?key={self.api_key}')
            return True
        except Exception:
            return False

    def complete_json(self, request: LLMRequest) -> dict[str, Any]:
        if request.evaluator_id == 'llm_rubric_induction':
            response = _rubric_induction_stub()
            response.update({'provider': 'gemini', 'model': self.model, 'note': 'rubric induction uses a bounded built-in scaffold'})
            return response
        payload = {
            'generationConfig': {
                'temperature': 0.1,
                'responseMimeType': 'application/json',
            },
            'contents': [
                {
                    'role': 'user',
                    'parts': [{'text': _json_only_prompt(request)}],
                }
            ],
        }
        raw = self._post_json(f'{self.base_url}/models/{self.model}:generateContent?key={self.api_key}', payload)
        parsed = self._extract_json_response(raw)
        parsed['provider'] = 'gemini'
        parsed['model'] = self.model
        return parsed

    def _extract_json_response(self, raw: dict[str, Any]) -> dict[str, Any]:
        candidates = raw.get('candidates') or []
        if not candidates:
            raise RuntimeError(f'Gemini returned no candidates: {raw}')
        content = candidates[0].get('content') or {}
        parts = content.get('parts') or []
        text_parts: list[str] = []
        for part in parts:
            txt = part.get('text')
            if txt:
                text_parts.append(str(txt))
        if not text_parts:
            raise RuntimeError(f'Gemini returned no text parts: {raw}')
        joined = '\n'.join(text_parts).strip()
        try:
            return json.loads(joined)
        except json.JSONDecodeError:
            m = re.search(r'\{.*\}', joined, flags=re.DOTALL)
            if not m:
                raise
            return json.loads(m.group(0))


class OpenRouterProvider(_HTTPJSONProvider):
    def __init__(self, model: str = 'openai/gpt-oss-20b:free', base_url: str = 'https://openrouter.ai/api/v1', api_key: str | None = None, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        super().__init__(base_url, timeout=timeout)
        self.model = model
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY', '')
        if not self.api_key:
            raise RuntimeError('OPENROUTER_API_KEY not configured')

    def complete_json(self, request: LLMRequest) -> dict[str, Any]:  # pragma: no cover
        if request.evaluator_id == 'llm_rubric_induction':
            response = _rubric_induction_stub()
            response.update({'provider': 'openrouter', 'model': self.model, 'note': 'rubric induction uses a bounded built-in scaffold'})
            return response
        content = _json_only_prompt(request)
        payload = {
            'model': self.model,
            'temperature': 0.1,
            'messages': [
                {'role': 'system', 'content': 'You are a bounded academic grading evaluator. Never output anything except JSON.'},
                {'role': 'user', 'content': content},
            ],
            'response_format': {'type': 'json_object'},
        }
        headers = {'Authorization': f'Bearer {self.api_key}', 'HTTP-Referer': os.getenv('OPENROUTER_SITE_URL', 'https://localhost'), 'X-Title': os.getenv('OPENROUTER_APP_NAME', 'autograde')}
        raw = self._post_json(f'{self.base_url}/chat/completions', payload, headers=headers)
        content_text = raw['choices'][0]['message']['content']
        parsed = json.loads(content_text)
        parsed['provider'] = 'openrouter'
        parsed['model'] = self.model
        return parsed


class OpenAIChatProvider:
    def __init__(self, model: str = 'gpt-4.1-mini') -> None:
        self.model = model
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise RuntimeError('openai package unavailable') from exc
        self._client = OpenAI()

    def complete_json(self, request: LLMRequest) -> dict[str, Any]:  # pragma: no cover
        if request.evaluator_id == 'llm_rubric_induction':
            response = _rubric_induction_stub()
            response.update({'provider': 'openai', 'model': self.model, 'note': 'rubric induction uses a bounded built-in scaffold'})
            return response
        content = _json_only_prompt(request)
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=0.1,
            messages=[
                {'role': 'system', 'content': 'You are a bounded academic grading evaluator. Never output anything except JSON.'},
                {'role': 'user', 'content': content},
            ],
            response_format={'type': 'json_object'},
        )
        parsed = json.loads(resp.choices[0].message.content)
        parsed['provider'] = 'openai'
        parsed['model'] = self.model
        return parsed


class LLMClient:
    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_default_provider()

    @property
    def provider_name(self) -> str:
        return type(self.provider).__name__

    @property
    def is_mock(self) -> bool:
        return isinstance(self.provider, MockLLMProvider)

    @property
    def is_live(self) -> bool:
        return not self.is_mock

    def _guard_mock(self) -> None:
        strict = os.getenv('AUTOGRADE_STRICT_LLM', '0').strip().lower() in {'1', 'true', 'yes'}
        if strict and self.is_mock:
            raise RuntimeError('MockLLMProvider selected while AUTOGRADE_STRICT_LLM is enabled. Configure Ollama/OpenRouter/OpenAI or disable strict mode.')

    def complete_json(self, request: LLMRequest) -> dict[str, Any]:
        return self.provider.complete_json(request)

    def evaluate(self, request: LLMRequest) -> LLMEvaluation:
        self._guard_mock()
        raw = self.complete_json(request)
        try:
            score = _clamp01(raw.get('score', 0.5))
            confidence = _clamp01(raw.get('confidence', 0.3))
            rationale = str(raw.get('rationale', 'LLM evaluator returned no rationale.'))[:2000]
            evidence_refs = [str(x) for x in raw.get('evidence_refs', request.evidence_refs)][:12]
        except Exception:
            score, confidence, rationale, evidence_refs = 0.5, 0.25, 'LLM response parsing failed; fallback output used.', request.evidence_refs[:8]
            raw = {'provider': 'fallback_parse_error'}
        return LLMEvaluation(request.evaluator_id, score, confidence, rationale, evidence_refs, raw)

    def extract_claims(self, request: LLMRequest) -> LLMClaimExtraction:
        self._guard_mock()
        raw = self.complete_json(request)
        claims: list[LLMClaimItem] = []
        for item in raw.get('claims', [])[:16]:
            try:
                claims.append(LLMClaimItem(
                    claim_type=str(item.get('claim_type', 'claim')),
                    subject=str(item.get('subject', 'unknown')),
                    value=str(item.get('value', '')),
                    confidence=_clamp01(item.get('confidence', 0.5)),
                    raw_text=str(item.get('raw_text', item.get('value', '')))[:500],
                ))
            except Exception:
                continue
        rationale = str(raw.get('rationale', ''))[:2000]
        return LLMClaimExtraction(claims=claims, rationale=rationale, raw=raw)

    def generate_feedback(self, request: LLMRequest) -> LLMFeedback:
        self._guard_mock()
        raw = self.complete_json(request)
        summary = str(raw.get('summary', ''))[:2400]
        strengths = [str(x)[:400] for x in raw.get('strengths', [])[:5]]
        weaknesses = [str(x)[:400] for x in raw.get('weaknesses', [])[:5]]
        suggestions = [str(x)[:400] for x in raw.get('suggestions', [])[:5]]
        return LLMFeedback(summary=summary, strengths=strengths, weaknesses=weaknesses, suggestions=suggestions, raw=raw)



def get_default_provider() -> LLMProvider:
    provider_name = os.getenv('AUTOGRADE_LLM_PROVIDER', 'auto').lower()
    model_name = os.getenv('AUTOGRADE_LLM_MODEL', '')
    allow_mock = os.getenv('AUTOGRADE_ALLOW_MOCK_LLM', '1').strip().lower() in {'1', 'true', 'yes'}

    if provider_name in {'mock', 'offline'}:
        return MockLLMProvider()

    def _maybe_mock(exc: Exception | None = None) -> LLMProvider:
        if allow_mock:
            return MockLLMProvider()
        if exc is not None:
            raise exc
        raise RuntimeError('No live LLM provider available and AUTOGRADE_ALLOW_MOCK_LLM is disabled.')

    if provider_name in {'auto', 'gemini'} and (os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or provider_name == 'gemini'):
        try:
            gemini = GeminiProvider(model=model_name or os.getenv('GEMINI_MODEL', 'gemini-3-flash-preview'))
            if provider_name != 'gemini' or gemini.is_available():
                return gemini
            if provider_name == 'gemini':
                return _maybe_mock(RuntimeError('Gemini requested but not reachable, and AUTOGRADE_ALLOW_MOCK_LLM is disabled.'))
        except Exception as exc:
            if provider_name == 'gemini':
                return _maybe_mock(exc)

    if provider_name in {'auto', 'ollama'}:
        try:
            ollama = OllamaProvider(model=model_name or os.getenv('OLLAMA_MODEL', 'qwen2.5:7b-instruct'))
            if provider_name != 'ollama':
                if ollama.is_available():
                    return ollama
            else:
                if ollama.is_available():
                    return ollama
                return _maybe_mock(RuntimeError('Ollama requested but not reachable, and AUTOGRADE_ALLOW_MOCK_LLM is disabled.'))
        except Exception as exc:
            if provider_name == 'ollama':
                return _maybe_mock(exc)

    if provider_name in {'auto', 'openrouter'} and (os.getenv('OPENROUTER_API_KEY') or provider_name == 'openrouter'):
        try:
            return OpenRouterProvider(model=model_name or os.getenv('OPENROUTER_MODEL', 'openai/gpt-oss-20b:free'))
        except Exception as exc:
            if provider_name == 'openrouter':
                return _maybe_mock(exc)

    if provider_name in {'auto', 'openai'} and (os.getenv('OPENAI_API_KEY') or provider_name == 'openai'):
        try:
            return OpenAIChatProvider(model=model_name or os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'))
        except Exception as exc:
            if provider_name == 'openai':
                return _maybe_mock(exc)

    return _maybe_mock()


def get_default_llm_client() -> LLMClient:
    return LLMClient()

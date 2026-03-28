from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from autograde.api.app import app
from autograde.api.demo import build_demo_rubric


def main() -> None:
    client = TestClient(app)

    r = client.get('/health')
    assert r.status_code == 200 and r.json()['status'] == 'ok'

    llm = client.get('/llm-status')
    assert llm.status_code == 200
    llm_data = llm.json()
    assert 'provider_class' in llm_data and 'is_mock' in llm_data

    rubric = build_demo_rubric()
    r = client.post('/validate-rubric', json={'rubric': {
        'assignment_id': rubric.assignment_id,
        'assignment_title': rubric.assignment_title,
        'required_artifacts': rubric.required_artifacts,
        'criteria': [
            {
                'criterion_id': c.criterion_id,
                'name': c.name,
                'description': c.description,
                'max_score': c.max_score,
                'weight': c.weight,
                'required_modalities': c.required_modalities,
                'evaluation_dimensions': c.evaluation_dimensions,
                'artifact_scope': c.artifact_scope,
                'evaluator_hints': c.evaluator_hints,
                'scoring_policy': {'mode': c.scoring_policy.mode, 'params': c.scoring_policy.params},
            }
            for c in rubric.criteria
        ],
        'normalize_to': rubric.normalize_to,
    }})
    data = r.json()
    assert r.status_code == 200 and data['is_valid'] is True

    sample = client.post('/demo-grade', json={'scenario': 'sample'})
    assert sample.status_code == 200
    sample_data = sample.json()
    assert sample_data['result']['final_score'] > 0
    assert sample_data['submission']['artifact_count'] >= 4

    contradiction = client.post('/demo-grade', json={'scenario': 'contradiction'})
    assert contradiction.status_code == 200
    contradiction_data = contradiction.json()
    assert contradiction_data['result']['final_score'] >= 0
    assert contradiction_data['submission']['artifact_count'] >= 4

    print('API smoke test passed.')
    print({
        'provider_class': llm_data['provider_class'],
        'sample_final_score': sample_data['result']['final_score'],
        'contradiction_final_score': contradiction_data['result']['final_score'],
    })


if __name__ == '__main__':
    main()

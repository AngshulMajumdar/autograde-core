from __future__ import annotations

import json
from io import BytesIO

from fastapi.testclient import TestClient

from autograde.api.app import app
from autograde.api.demo import build_demo_rubric, rubric_to_payload


client = TestClient(app)


def test_frontend_home_renders() -> None:
    response = client.get('/')
    assert response.status_code == 200
    assert 'Autograde Core Demo' in response.text
    assert 'Upload and grade' in response.text


def test_grade_upload_endpoint_with_sample_files() -> None:
    rubric_payload = rubric_to_payload(build_demo_rubric())
    files = [
        ('files', ('report.txt', BytesIO(b'Title: Report\nWe implemented Dijkstra algorithm and explain it clearly.'), 'text/plain')),
        ('files', ('main.py', BytesIO(b'def dijkstra(graph, src):\n    return {src: 0}\n'), 'text/x-python')),
        ('files', ('results.csv', BytesIO(b'dataset,accuracy\ntoy,0.95\n'), 'text/csv')),
    ]
    data = {
        'assignment_id': 'CS301_A2',
        'submission_id': 'upload_case_001',
        'student_id': 'student_demo',
        'rubric_json': json.dumps(rubric_payload),
    }
    response = client.post('/grade-upload', data=data, files=files)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload['submission']['artifact_count'] == 3
    assert payload['result']['final_score'] >= 0

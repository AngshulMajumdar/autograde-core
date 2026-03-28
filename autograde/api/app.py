from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from autograde.api.demo import build_demo_rubric, rubric_to_payload
from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.llm.client import get_default_llm_client
from autograde.rubric import Criterion, Rubric, RubricValidator, ScoringPolicy
from autograde.utils.sample_data import build_contradictory_submission, build_sample_submission

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / 'templates'))

app = FastAPI(title='Autograde Core API', version='0.2.0')
app.mount('/static', StaticFiles(directory=str(BASE_DIR / 'static')), name='static')


class GradePathRequest(BaseModel):
    assignment_id: str
    submission_path: str
    submission_id: str = 'submission_001'
    student_id: str | None = None
    rubric: dict[str, Any]


class DemoGradeRequest(BaseModel):
    scenario: str = Field(default='sample', pattern='^(sample|contradiction)$')


class ValidateRubricRequest(BaseModel):
    rubric: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


def _criterion_from_dict(payload: dict[str, Any]) -> Criterion:
    scoring_policy = payload.get('scoring_policy') or {}
    return Criterion(
        criterion_id=str(payload['criterion_id']),
        name=str(payload['name']),
        description=str(payload.get('description', '')),
        max_score=float(payload['max_score']),
        weight=float(payload['weight']),
        required_modalities=list(payload.get('required_modalities', [])),
        evaluation_dimensions=list(payload.get('evaluation_dimensions', [])),
        artifact_scope=list(payload.get('artifact_scope', [])),
        evaluator_hints=list(payload.get('evaluator_hints', [])),
        cross_checks=list(payload.get('cross_checks', [])),
        required_evidence_types=list(payload.get('required_evidence_types', [])),
        supporting_evidence_types=list(payload.get('supporting_evidence_types', [])),
        required_tags=list(payload.get('required_tags', [])),
        supporting_tags=list(payload.get('supporting_tags', [])),
        minimum_evidence_count=int(payload.get('minimum_evidence_count', 1)),
        zero_if_missing=bool(payload.get('zero_if_missing', False)),
        cross_check_policy=str(payload.get('cross_check_policy', 'advisory')),
        contradiction_policy=str(payload.get('contradiction_policy', 'discount')),
        contradiction_severity_threshold=str(payload.get('contradiction_severity_threshold', 'medium')),
        depends_on=list(payload.get('depends_on', [])),
        manual_review_conditions=list(payload.get('manual_review_conditions', [])),
        scoring_policy=ScoringPolicy(
            mode=str(scoring_policy.get('mode', 'analytic_bands')),
            params=dict(scoring_policy.get('params', {})),
        ),
        integrity_policy=str(payload.get('integrity_policy', 'review_only')),
        integrity_scope=str(payload.get('integrity_scope', 'auto')),
        integrity_severity_threshold=str(payload.get('integrity_severity_threshold', 'medium')),
        metadata=dict(payload.get('metadata', {})),
    )



def _rubric_from_dict(payload: dict[str, Any]) -> Rubric:
    return Rubric(
        assignment_id=str(payload['assignment_id']),
        assignment_title=str(payload.get('assignment_title', payload['assignment_id'])),
        required_artifacts=list(payload.get('required_artifacts', [])),
        criteria=[_criterion_from_dict(item) for item in payload.get('criteria', [])],
        aggregation_mode=str(payload.get('aggregation_mode', 'weighted_sum')),
        normalize_to=float(payload.get('normalize_to', 100.0)),
        low_confidence_threshold=float(payload.get('low_confidence_threshold', 0.65)),
        adaptive_weighting_enabled=bool(payload.get('adaptive_weighting_enabled', False)),
        adaptive_weighting_params=dict(payload.get('adaptive_weighting_params', {})),
    )



def _llm_status() -> dict[str, Any]:
    client = get_default_llm_client()
    provider = client.provider
    status: dict[str, Any] = {
        'provider_class': provider.__class__.__name__,
        'provider_name': getattr(provider, '__class__', type(provider)).__name__,
        'is_mock': client.is_mock,
        'is_live': client.is_live,
        'configured_provider': 'gemini' if 'Gemini' in provider.__class__.__name__ else ('ollama' if 'Ollama' in provider.__class__.__name__ else ('openrouter' if 'OpenRouter' in provider.__class__.__name__ else ('openai' if 'OpenAI' in provider.__class__.__name__ else 'mock'))),
        'env_provider': os.getenv('AUTOGRADE_LLM_PROVIDER', 'auto'),
        'strict_mode': os.getenv('AUTOGRADE_STRICT_LLM', '0'),
        'allow_mock': os.getenv('AUTOGRADE_ALLOW_MOCK_LLM', '1'),
    }
    for attr in ('model', 'base_url'):
        if hasattr(provider, attr):
            status[attr] = getattr(provider, attr)
    return status



def _grade_directory(assignment_id: str, submission_dir: Path, rubric_payload: dict[str, Any], submission_id: str, student_id: str | None = None) -> dict[str, Any]:
    rubric = _rubric_from_dict(rubric_payload)
    validation = RubricValidator().validate(rubric)
    if not validation.is_valid:
        raise HTTPException(status_code=400, detail={'errors': validation.errors, 'warnings': validation.warnings})
    pipeline = SubmissionIngestionPipeline()
    executor = GradingExecutor()
    submission = pipeline.ingest_submission(
        assignment_id=assignment_id,
        submission_path=str(submission_dir),
        submission_id=submission_id,
        student_id=student_id,
    )
    result = executor.grade_submission(submission, rubric)
    return {
        'submission': {
            'submission_id': submission.submission_id,
            'artifact_count': len(submission.artifacts),
            'evidence_count': len(submission.evidence),
            'processing_status': submission.processing_status,
            'unsupported_artifacts': submission.manifest.unsupported_artifacts,
            'extraction_warnings': submission.manifest.extraction_warnings,
        },
        'result': asdict(result),
    }


@app.get('/', response_class=HTMLResponse)
def frontend_home(request: Request) -> HTMLResponse:
    demo_rubric = rubric_to_payload(build_demo_rubric())
    context = {
        'request': request,
        'demo_rubric_json': json.dumps(demo_rubric, indent=2),
        'llm_status': _llm_status(),
    }
    return TEMPLATES.TemplateResponse(request, 'index.html', context)


@app.get('/health', response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status='ok', service='autograde-core-api', version=app.version)


@app.get('/llm-status')
def llm_status() -> dict[str, Any]:
    return _llm_status()


@app.get('/version')
def version() -> dict[str, str]:
    return {'version': app.version}


@app.post('/validate-rubric')
def validate_rubric(request: ValidateRubricRequest) -> dict[str, Any]:
    rubric = _rubric_from_dict(request.rubric)
    result = RubricValidator().validate(rubric)
    return asdict(result)


@app.post('/grade')
def grade(request: GradePathRequest) -> dict[str, Any]:
    submission_root = Path(request.submission_path)
    if not submission_root.exists():
        raise HTTPException(status_code=400, detail=f'Submission path does not exist: {submission_root}')
    return _grade_directory(
        assignment_id=request.assignment_id,
        submission_dir=submission_root,
        rubric_payload=request.rubric,
        submission_id=request.submission_id,
        student_id=request.student_id,
    )


@app.post('/grade-upload')
async def grade_upload(
    assignment_id: str = Form(...),
    submission_id: str = Form('submission_upload_001'),
    student_id: str | None = Form(None),
    rubric_json: str = Form(...),
    files: list[UploadFile] = File(...),
) -> dict[str, Any]:
    try:
        rubric_payload = json.loads(rubric_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f'Invalid rubric JSON: {exc}') from exc

    with TemporaryDirectory(prefix='autograde_upload_') as tmpdir:
        root = Path(tmpdir)
        for upload in files:
            safe_name = Path(upload.filename or 'uploaded_file').name
            target = root / safe_name
            data = await upload.read()
            target.write_bytes(data)
        return _grade_directory(
            assignment_id=assignment_id,
            submission_dir=root,
            rubric_payload=rubric_payload,
            submission_id=submission_id,
            student_id=student_id,
        )


@app.post('/demo-grade')
def demo_grade(request: DemoGradeRequest) -> dict[str, Any]:
    rubric = build_demo_rubric()
    with TemporaryDirectory(prefix='autograde_demo_') as tmpdir:
        if request.scenario == 'contradiction':
            build_contradictory_submission(tmpdir)
        else:
            build_sample_submission(tmpdir)
        return {
            'scenario': request.scenario,
            **_grade_directory(
                assignment_id=rubric.assignment_id,
                submission_dir=Path(tmpdir),
                rubric_payload=rubric_to_payload(rubric),
                submission_id=f'demo_{request.scenario}',
                student_id='demo_student',
            ),
        }

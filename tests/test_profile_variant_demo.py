from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from autograde.executor import GradingExecutor
from autograde.ingestion import SubmissionIngestionPipeline
from autograde.subjects.registry import get_subject_profile
from autograde.utils.sample_data import build_sample_submission


def test_programming_variant_demo() -> None:
    profile = get_subject_profile("programming")
    rubric = profile.build_rubric("data_science_notebook", assignment_id="DS1", assignment_title="Notebook")
    submission_dir = ROOT / "tests" / "runtime_ds_submission"
    build_sample_submission(submission_dir)
    submission = SubmissionIngestionPipeline().ingest_submission("sub_ds", "student_ds", str(submission_dir))
    result = GradingExecutor().grade_submission(submission, rubric)
    assert len(result.criterion_results) == 5
    assert result.final_score >= 0

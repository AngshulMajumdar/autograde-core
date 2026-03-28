from datetime import datetime

from autograde.subjects.registry import get_subject_profile
from autograde.models.base import EvidenceObject, Submission, Location
from autograde.executor.engine import GradingExecutor


def _ev(eid, modality, content='', structured=None, subtype='paragraph'):
    return EvidenceObject(evidence_id=eid, submission_id='s1', artifact_id='a1', modality=modality, subtype=subtype, content=content, structured_content=structured or {}, preview=content[:80] if content else None, location=Location(file='report.txt'), confidence=0.9, extractor_id='test', tags=[], links=[])


def test_engineering_labs_profile_builds_and_grades():
    profile = get_subject_profile('engineering_labs')
    rubric = profile.build_rubric('ee_lab_report', 'EE101-L1', 'Diode Characteristics Lab')
    submission = Submission(submission_id='s1', assignment_id='EE101-L1', student_id='st1', submitted_at=datetime.utcnow())
    for ev in [
        _ev('t1', 'text', 'Apparatus: power supply, multimeter, resistor, diode. Setup connection and procedure to measure voltage and current. Observation table is given. Formula used for dynamic resistance calculation. Expected and measured values show deviation due to instrument error. Precaution: calibrate and avoid loose connections.'),
        _ev('d1', 'diagram', structured={'detected_components':['input_node','output_node','resistor','diode'], 'diagram_family':'measurement_setup'}),
        _ev('tb1', 'table', 'Vin(V), I(mA)\n0.2,0.1\n0.4,0.5\n0.6,1.1\n', {'header':['Vin(V)','I(mA)'], 'row_count':3, 'metrics':{'voltage':0.6,'current':1.1}}),
        _ev('eq1', 'equation', 'R_d = dV/dI', subtype='math_ocr'),
    ]:
        submission.add_evidence(ev)
    ex = GradingExecutor()
    result = ex.grade_submission(submission, rubric)
    assert result.final_score > 0
    assert any(c.criterion_id == 'EL4' for c in result.criterion_results)

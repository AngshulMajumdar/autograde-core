from datetime import datetime

from autograde.subjects.registry import get_subject_profile
from autograde.models.base import EvidenceObject, Submission, Location
from autograde.executor.engine import GradingExecutor


def _ev(eid, modality, content='', structured=None, subtype='paragraph'):
    return EvidenceObject(
        evidence_id=eid,
        submission_id='s1',
        artifact_id='a1',
        modality=modality,
        subtype=subtype,
        content=content,
        structured_content=structured or {},
        preview=content[:80] if content else None,
        location=Location(file='report.txt'),
        confidence=0.9,
        extractor_id='test',
        tags=[],
        links=[],
    )


def test_communication_vlsi_profile_builds_and_grades():
    profile = get_subject_profile('communication_vlsi_labs')
    rubric = profile.build_rubric('communication_lab', 'EC301-L1', 'AM Modulation Lab')
    submission = Submission(submission_id='s1', assignment_id='EC301-L1', student_id='st1', submitted_at=datetime.utcnow())
    for ev in [
        _ev('t1', 'text', 'The observed waveform and spectrum show carrier and sidebands. Measured bandwidth and gain are compared with expected values. The deviation is small. Timing and logic are not relevant here but frequency and amplitude are discussed.'),
        _ev('img1', 'image', 'waveform spectrum plot with frequency and amplitude labels'),
        _ev('tb1', 'table', 'gain,bandwidth\n9.8,5.1kHz', {'header':['gain','bandwidth'], 'row_count':1, 'metrics':{'gain':9.8,'bandwidth':5100}}),
    ]:
        submission.add_evidence(ev)
    result = GradingExecutor().grade_submission(submission, rubric)
    assert result.final_score > 0
    assert any(c.criterion_id == 'CV2' for c in result.criterion_results)


def test_embedded_systems_profile_builds_and_grades():
    profile = get_subject_profile('embedded_systems_labs')
    rubric = profile.build_rubric('embedded_system_lab', 'EC402-L2', 'Sensor Logging Lab')
    submission = Submission(submission_id='s2', assignment_id='EC402-L2', student_id='st2', submitted_at=datetime.utcnow())
    for ev in [
        _ev('t1', 'text', 'The system reads a temperature sensor using ADC and shows the value on serial UART output. When the threshold is crossed, the LED actuator turns on. Timer interrupt is used for periodic sampling.'),
        _ev('c1', 'code', 'void setup(){ Serial.begin(9600); pinMode(LED_BUILTIN, OUTPUT); } void loop(){ int x=analogRead(A0); if(x>500){ digitalWrite(LED_BUILTIN, HIGH);} }', subtype='function'),
        _ev('e1', 'execution', structured={'tests_run':2,'tests_passed':2}, subtype='unit_test_result'),
    ]:
        submission.add_evidence(ev)
    result = GradingExecutor().grade_submission(submission, rubric)
    assert result.final_score > 0
    assert any(c.criterion_id == 'EM1' for c in result.criterion_results)

from __future__ import annotations

from autograde.rubric.induction import PastCase, induce_rubric_from_past_cases
from autograde.rubric.drift import RubricDriftDetector


def main() -> None:
    baseline_cases = [
        PastCase('Correct code, weak explanation.', 'Correctness is good but explanation is weak.', 70),
        PastCase('Good code and decent analysis.', 'Strong correctness and some analysis.', 82),
    ]
    recent_cases = [
        PastCase('Correct code, strong results discussion.', 'Correctness is strong and result interpretation matters a lot.', 84),
        PastCase('Correct code, poor analysis.', 'Missing analysis and interpretation of outcomes.', 68),
    ]
    baseline = induce_rubric_from_past_cases(baseline_cases, 'programming')
    detector = RubricDriftDetector()
    report = detector.induce_and_compare(baseline, recent_cases, 'programming')
    print('significant_drift=', report.significant_drift)
    print('added=', report.added)
    print('removed=', report.removed)
    for item in report.changed:
        print(item)


if __name__ == '__main__':
    main()

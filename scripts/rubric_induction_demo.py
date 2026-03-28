from __future__ import annotations

from autograde.rubric.induction import PastCase, induce_rubric_from_past_cases


def main() -> None:
    cases = [
        PastCase(
            submission_summary='Correct implementation, weak explanation, missing comparison.',
            feedback='Implementation is mostly correct, but the analysis and comparison with baseline are missing.',
            score=72,
        ),
        PastCase(
            submission_summary='Strong explanation and analysis, but implementation has correctness errors.',
            feedback='The writeup is clear, but the code behavior is not correct on important test cases.',
            score=61,
        ),
        PastCase(
            submission_summary='Excellent correctness, good explanation, reasonable analysis.',
            feedback='Strong submission overall. Correct solution with clear reasoning and adequate result discussion.',
            score=88,
        ),
    ]
    rubric = induce_rubric_from_past_cases(cases, subject_profile='programming')
    print(rubric.assignment_title)
    for criterion in rubric.criteria:
        print(criterion.criterion_id, criterion.name, round(criterion.weight, 3), criterion.evaluator_hints)


if __name__ == '__main__':
    main()

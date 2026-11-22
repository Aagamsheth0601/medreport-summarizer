"""Render supplied-range comparisons from validated synthetic measurements."""

from schemas import Analysis, Extraction, TestResult


def _render_measurement(test: TestResult) -> str:
    value = str(test.value).removesuffix(".0")
    measurement = f"{test.test_name} measured {value} {test.unit}"
    if test.is_at_excluded_cutoff():
        return f"{measurement}, exactly at the excluded cutoff ({test.reference_text})."
    if test.reference_range is None:
        return f"{measurement}, with no supplied reference range."
    relation = {"low": "below", "normal": "within", "high": "above"}[test.status]
    return f"{measurement}, {relation} the supplied range ({test.reference_text})."


def cutoff_finding_evidence(extraction: Extraction, analysis: Analysis) -> dict[int, str]:
    """Return evidence for findings that cite a strict boundary equality."""
    tests_by_name = {test.test_name: test for test in extraction.tests}
    evidence = {}
    for finding_id, finding in enumerate(analysis.findings, start=1):
        cited_tests = [tests_by_name[name] for name in finding.related_tests]
        if any(test.is_at_excluded_cutoff() for test in cited_tests):
            evidence[finding_id] = " ".join(_render_measurement(test) for test in cited_tests)
    return evidence

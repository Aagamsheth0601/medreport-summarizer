import copy

import pytest

from agents import PipelineError
from benchmark import load_cases, run_attempt
from test_pipeline import FakeClient


class MeteredFake(FakeClient):
    last_total_tokens = None

    def generate(self, stage, prompt, contents, schema):
        self.last_total_tokens = None
        text = super().generate(stage, prompt, contents, schema)
        self.last_total_tokens = 10
        return text


@pytest.fixture
def routine():
    return load_cases()[0]


def routine_responses(case):
    extraction = case.expected.model_dump()
    analysis = {
        "panels": [{
            "panel_name": "Synthetic panel",
            "tests": [test.test_name for test in case.expected.tests],
            "panel_summary": "All reported values are within the supplied ranges.",
        }],
        "findings": [],
        "limitations": ["Only the supplied synthetic ranges apply."],
    }
    explanation = {
        "quick_summary": "This is a synthetic panel.",
        "findings_explained": [],
        "within_range": "All reported values are within the supplied ranges.",
        "limitations": "AI can make mistakes.",
    }
    return extraction, analysis, explanation


def test_both_modes_use_the_same_source_and_record_usage(routine):
    extraction, analysis, explanation = routine_responses(routine)
    single = MeteredFake([dict(extraction=extraction, analysis=analysis, explanation=explanation)])
    three = MeteredFake([extraction, analysis, explanation])

    single_attempt = run_attempt(routine, "single-call", single)
    three_attempt = run_attempt(routine, "three-agent", three)

    assert single.calls[0][1] == three.calls[0][1] == routine.report
    assert (single_attempt.model_calls, single_attempt.total_tokens) == (1, 10)
    assert (three_attempt.model_calls, three_attempt.total_tokens) == (3, 30)
    assert single_attempt.extraction_verified and three_attempt.extraction_verified
    assert single_attempt.error is None and three_attempt.error is None
    assert single_attempt.result == three_attempt.result


def test_single_call_uses_the_exact_extraction_check(routine):
    extraction, analysis, explanation = routine_responses(routine)
    changed = copy.deepcopy(extraction)
    changed["tests"][0]["value"] = 6.5
    client = MeteredFake([dict(extraction=changed, analysis=analysis, explanation=explanation)])

    attempt = run_attempt(routine, "single-call", client)

    assert "verified values" in attempt.error
    assert not attempt.extraction_verified
    assert attempt.result is None
    assert attempt.total_tokens == 10


def test_failed_calls_keep_failure_and_leave_total_tokens_unknown(routine):
    extraction, _, _ = routine_responses(routine)
    client = MeteredFake([extraction, PipelineError("Interpreter", "HTTP 503")])

    attempt = run_attempt(routine, "three-agent", client)

    assert attempt.extraction_verified
    assert attempt.model_calls == 2
    assert attempt.total_tokens is None
    assert attempt.result is None
    assert attempt.error == "Interpreter: HTTP 503"


def test_both_modes_ground_the_same_cutoff_finding():
    case = next(case for case in load_cases() if case.sample_id == "cutoffs-and-missing-range")
    extraction, analysis, explanation = routine_responses(case)
    wrong = "Triglycerides are above 150 mg/dL."
    analysis["panels"][0]["panel_summary"] = "See the supplied ranges."
    analysis["findings"] = [{
        "finding": wrong, "related_tests": ["Triglycerides"], "rationale": wrong,
    }]
    explanation["within_range"] = "Albumin and Glucose are within their supplied ranges."
    explanation["findings_explained"] = [{"finding_id": 1, "text": wrong}]
    single = MeteredFake([dict(extraction=extraction, analysis=analysis, explanation=explanation)])
    three = MeteredFake([extraction, analysis, explanation])

    single_attempt = run_attempt(case, "single-call", single)
    three_attempt = run_attempt(case, "three-agent", three)

    expected = "Triglycerides measured 150 mg/dL, exactly at the excluded cutoff (< 150)."
    assert single_attempt.result is not None
    assert single_attempt.result == three_attempt.result
    assert single_attempt.result.analysis.findings[0].rationale == expected
    assert single_attempt.result.explanation.findings_explained == [expected]
    assert wrong not in single_attempt.result.summary_markdown

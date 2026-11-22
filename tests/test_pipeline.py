import json

import pytest

from agents import PipelineError
from pipeline import run_pipeline
from samples import SAMPLE_IDS, load_sample
from schemas import DISCLAIMER


class FakeClient:
    """Scripted responses exercise orchestration, not Gemini's medical accuracy."""
    model = "test-double"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def generate(self, stage, prompt, contents, schema):
        self.calls.append((stage, contents))
        result = next(self.responses)
        if isinstance(result, Exception):
            raise result
        return json.dumps(result) if isinstance(result, dict) else result


def responses_for(sample_id):
    _, expected = load_sample(sample_id)
    abnormal = [test.test_name for test in expected.tests if test.status in {"low", "high"}]
    analysis = {
        "panels": [{"panel_name": "Sample panel", "tests": [t.test_name for t in expected.tests],
                    "panel_summary": "Synthetic measurements grouped for this test."}],
        "findings": ([{"finding": "Sample values outside their ranges", "related_tests": abnormal,
                       "rationale": "These sample values fall outside their supplied ranges."}] if abnormal else []),
        "limitations": ["Synthetic values cannot establish health."],
    }
    findings_explained = (
        [{"finding_id": 1, "text": "Sample values outside their ranges."}] if abnormal else []
    )
    explanation = dict(quick_summary="This is a synthetic example.",
                       findings_explained=findings_explained,
                       within_range="See the supplied ranges.", limitations="AI can make mistakes.")
    return [expected.model_dump(), analysis, explanation]


@pytest.mark.parametrize("sample_id", SAMPLE_IDS)
def test_full_pipeline_passes_evidence_and_progress(sample_id):
    client = FakeClient(responses_for(sample_id))
    events = []
    result = run_pipeline(sample_id, client, lambda *event: events.append(event))
    assert [call[0] for call in client.calls] == ["Extractor", "Interpreter", "Communicator"]
    assert events == [(stage, state) for stage in ("Extractor", "Interpreter", "Communicator")
                      for state in ("started", "completed")]
    assert json.loads(client.calls[1][1]) == result.extraction.model_dump()
    assert json.loads(client.calls[2][1])["extraction"] == result.extraction.model_dump()
    assert result.summary_markdown.startswith(DISCLAIMER)


@pytest.mark.parametrize("raw", [None, "", "  ", "not json", "{}", '{"tests": []}'])
def test_bad_extraction_stops_before_interpreter(raw):
    client = FakeClient([raw])
    with pytest.raises(PipelineError, match="Extractor"):
        run_pipeline("within-range", client)
    assert len(client.calls) == 1


@pytest.mark.parametrize("mutation", ["missing", "changed", "unit", "extra"])
def test_ground_truth_rejects_plausible_but_wrong_extraction(mutation):
    responses = responses_for("within-range")
    tests = responses[0]["tests"]
    if mutation == "missing":
        tests.pop()
    elif mutation == "changed":
        tests[0]["value"] = 14.6  # Still in range, but not the printed value.
    elif mutation == "unit":
        tests[0]["unit"] = "mg/dL"
    else:
        tests.append({**tests[0], "test_name": "Invented test"})
    client = FakeClient(responses)
    with pytest.raises(PipelineError, match="verified values"):
        run_pipeline("within-range", client)
    assert len(client.calls) == 1


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "invented", "finding"])
def test_reject_invalid_interpreter_links(mutation):
    responses = responses_for("within-range")
    panel = responses[1]["panels"][0]
    if mutation == "missing":
        panel["tests"].pop()
    elif mutation == "duplicate":
        panel["tests"].append(panel["tests"][0])
    elif mutation == "invented":
        panel["tests"][0] = "Invented test"
    else:
        responses[1]["findings"] = [{"finding": "Unsupported", "related_tests": ["Invented"],
                                     "rationale": "Unsupported rationale"}]
    client = FakeClient(responses)
    with pytest.raises(PipelineError, match="Interpreter"):
        run_pipeline("within-range", client)
    assert len(client.calls) == 2


def test_reject_missing_finding_explanation():
    responses = responses_for("mixed-patterns")
    responses[2]["findings_explained"] = []
    with pytest.raises(PipelineError, match="Communicator"):
        run_pipeline("mixed-patterns", FakeClient(responses))


def responses_with_two_findings():
    responses = responses_for("mixed-patterns")
    responses[1]["findings"].append({
        "finding": "An additional finding",
        "related_tests": ["Hemoglobin"],
        "rationale": "This finding needs its own explanation.",
    })
    responses[2]["findings_explained"].append({
        "finding_id": 2,
        "text": "An explanation for the additional finding.",
    })
    return responses


def test_reject_repeated_untagged_explanation_with_matching_count():
    responses = responses_with_two_findings()
    responses[2]["findings_explained"] = ["Only the first finding is explained."] * 2

    with pytest.raises(PipelineError, match="Communicator"):
        run_pipeline("mixed-patterns", FakeClient(responses))


@pytest.mark.parametrize("finding_ids", [(1, 1), (1, 3), (1, 2, 2)])
def test_reject_incorrect_finding_id_coverage(finding_ids):
    responses = responses_with_two_findings()
    responses[2]["findings_explained"] = [
        {"finding_id": finding_id, "text": f"Explanation {index}."}
        for index, finding_id in enumerate(finding_ids, start=1)
    ]

    with pytest.raises(PipelineError, match="every finding ID exactly once"):
        run_pipeline("mixed-patterns", FakeClient(responses))


def test_explanations_are_saved_in_finding_order():
    responses = responses_with_two_findings()
    expected = [entry["text"] for entry in responses[2]["findings_explained"]]
    responses[2]["findings_explained"].reverse()
    client = FakeClient(responses)

    result = run_pipeline("mixed-patterns", client)

    numbered_findings = json.loads(client.calls[2][1])["analysis"]["findings"]
    assert [finding["finding_id"] for finding in numbered_findings] == [1, 2]
    assert result.explanation.findings_explained == expected
    assert result.summary_markdown.index(expected[0]) < result.summary_markdown.index(expected[1])


def test_cutoff_finding_uses_validated_evidence_instead_of_wrong_wording():
    responses = responses_for("range-boundaries")
    responses[1]["findings"][0]["related_tests"].extend(["Fasting Blood Sugar", "Vitamin B12"])
    responses[1]["findings"].append({
        "finding": "A finding with no strict cutoff hit",
        "related_tests": ["eGFR"],
        "rationale": "This value equals an inclusive lower bound.",
    })
    wrong = "Total Cholesterol is above 200 mg/dL and HDL Cholesterol is below 40 mg/dL."
    responses[1]["findings"][0]["finding"] = "Above and below the cutoffs"
    responses[1]["findings"][0]["rationale"] = wrong
    ordinary = "The eGFR meets its supplied minimum."
    responses[2]["findings_explained"] = [
        {"finding_id": 1, "text": wrong},
        {"finding_id": 2, "text": ordinary},
    ]

    client = FakeClient(responses)
    result = run_pipeline("range-boundaries", client)

    boundary, other = result.explanation.findings_explained
    assert "Total Cholesterol measured 200 mg/dL, exactly at the excluded cutoff (< 200)." in boundary
    assert "HDL Cholesterol measured 40 mg/dL, exactly at the excluded cutoff (> 40)." in boundary
    assert "Fasting Blood Sugar measured 100 mg/dL, within the supplied range (70 - 100)." in boundary
    assert "Vitamin B12 measured 250 pg/mL, with no supplied reference range." in boundary
    assert other == ordinary
    assert result.analysis.findings[0].finding == "At an excluded cutoff"
    assert result.analysis.findings[0].rationale == boundary
    assert result.analysis.findings[1].rationale == responses[1]["findings"][1]["rationale"]
    assert json.loads(client.calls[2][1])["analysis"]["findings"][0]["rationale"] == boundary
    assert boundary in result.summary_markdown
    assert wrong not in result.summary_markdown


def test_abnormal_results_cannot_disappear_from_findings():
    responses = responses_for("mixed-patterns")
    responses[1]["findings"][0]["related_tests"].remove("Hemoglobin")
    with pytest.raises(PipelineError, match="omitted an out-of-range"):
        run_pipeline("mixed-patterns", FakeClient(responses))


@pytest.mark.parametrize("sample_id", ["../../.env", "report.pdf", "", "unknown"])
def test_no_arbitrary_report_input(sample_id):
    client = FakeClient([])
    with pytest.raises(PipelineError, match="built-in"):
        run_pipeline(sample_id, client)
    assert not client.calls


def test_failure_does_not_report_stage_completed():
    responses = responses_for("within-range")
    responses[1] = PipelineError("Interpreter", "Request timed out")
    events = []
    with pytest.raises(PipelineError):
        run_pipeline("within-range", FakeClient(responses), lambda *e: events.append(e))
    assert events[-1] == ("Interpreter", "started")

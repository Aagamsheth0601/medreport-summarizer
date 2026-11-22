"""Agent 3: explain evidence; application code supplies the disclaimer."""

import json
from agents import PipelineError
from agents.range_evidence import cutoff_finding_evidence
from llm import ModelClient, generate_validated
from schemas import Analysis, CommunicatorResponse, DISCLAIMER, Explanation, Extraction

SYSTEM_PROMPT = """Explain this SYNTHETIC report analysis in accessible language.
You receive both original extracted evidence and the analysis. Address the sample,
not the reader as a patient. Return one findings_explained entry per finding, with
its exact finding_id and explanatory text. Return an empty list for zero findings.
Do not add findings, values, diagnoses, triage, care schedules, or treatment advice.
Explain jargon. Describe within-range results without claiming the person is healthy.
Preserve uncertainty and mention that AI can make mistakes.
Return plain text in each schema field, without HTML or Markdown headings.
"""


def communicate(extraction: Extraction, analysis: Analysis, client: ModelClient) -> Explanation:
    analysis_input = analysis.model_dump()
    expected_ids = range(1, len(analysis.findings) + 1)
    analysis_input["findings"] = [
        {"finding_id": finding_id, **finding}
        for finding_id, finding in zip(expected_ids, analysis_input["findings"])
    ]
    contents = json.dumps({"extraction": extraction.model_dump(), "analysis": analysis_input})
    response = generate_validated(
        client, "Communicator", SYSTEM_PROMPT, contents, CommunicatorResponse
    )
    return verify_explanations(extraction, analysis, response)


def verify_explanations(
    extraction: Extraction, analysis: Analysis, response: CommunicatorResponse
) -> Explanation:
    expected_ids = range(1, len(analysis.findings) + 1)
    explanations = {entry.finding_id: entry.text for entry in response.findings_explained}
    if (
        explanations.keys() != set(expected_ids)
        or len(explanations) != len(response.findings_explained)
    ):
        raise PipelineError(
            "Communicator", "The explanation must reference every finding ID exactly once."
        )

    # Replace the whole cutoff explanation so contrary model wording cannot survive beside it.
    explanations.update(cutoff_finding_evidence(extraction, analysis))

    # Keep the report format compatible with recorded runs and the frontend.
    return Explanation(
        quick_summary=response.quick_summary,
        findings_explained=[explanations[finding_id] for finding_id in expected_ids],
        within_range=response.within_range,
        limitations=response.limitations,
    )


def render_summary(explanation: Explanation) -> str:
    """Fixed headings and notice cannot disappear because the model omitted them."""
    findings = "\n\n".join(explanation.findings_explained) or "No out-of-range pattern was identified in this sample."
    return (
        f"{DISCLAIMER}\n\n## Quick summary\n{explanation.quick_summary}"
        f"\n\n## Patterns in this sample\n{findings}"
        f"\n\n## Results within the supplied ranges\n{explanation.within_range}"
        f"\n\n## Limitations\n{explanation.limitations}\n"
    )

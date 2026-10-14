"""Agent 3: explain evidence; application code supplies the disclaimer."""

import json
from agents import PipelineError
from llm import ModelClient, generate_validated
from schemas import Analysis, DISCLAIMER, Explanation, Extraction

SYSTEM_PROMPT = """Explain this SYNTHETIC report analysis in accessible language.
You receive both original extracted evidence and the analysis. Address the sample,
not the reader as a patient. Explain each finding in order (one findings_explained
entry per finding). Do not add findings, values, diagnoses, triage, care schedules,
or treatment advice. Explain jargon. Describe within-range results without claiming
the person is healthy. Preserve uncertainty and mention that AI can make mistakes.
Return plain text in each schema field, without HTML or Markdown headings.
"""


def communicate(extraction: Extraction, analysis: Analysis, client: ModelClient) -> Explanation:
    contents = json.dumps({"extraction": extraction.model_dump(), "analysis": analysis.model_dump()})
    explanation = generate_validated(client, "Communicator", SYSTEM_PROMPT, contents, Explanation)
    if len(explanation.findings_explained) != len(analysis.findings):
        raise PipelineError("Communicator", "The explanation must cover every finding exactly once.")
    return explanation


def render_summary(explanation: Explanation) -> str:
    """Fixed headings and notice cannot disappear because the model omitted them."""
    findings = "\n\n".join(explanation.findings_explained) or "No out-of-range pattern was identified in this sample."
    return (
        f"{DISCLAIMER}\n\n## Quick summary\n{explanation.quick_summary}"
        f"\n\n## Patterns in this sample\n{findings}"
        f"\n\n## Results within the supplied ranges\n{explanation.within_range}"
        f"\n\n## Limitations\n{explanation.limitations}\n"
    )

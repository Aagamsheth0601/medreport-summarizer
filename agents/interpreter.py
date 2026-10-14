"""Agent 2: explain relationships, with references back to extracted tests."""

from collections import Counter
from agents import PipelineError
from llm import ModelClient, generate_validated
from schemas import Analysis, Extraction

SYSTEM_PROMPT = """Analyze a SYNTHETIC report for an educational portfolio demo.
Group every test into exactly one panel. Use exact test names from the input.
Describe notable out-of-reference-range results and relationships between tests.
Every finding must cite related_tests from the input and explain its evidence.
Every low or high test must appear in at least one finding's related_tests.
Do not invent tests, values, diagnoses, severity, urgency, appointment timing,
treatment, or personal recommendations. Do not infer overall health from normal
results. Missing ranges mean unknown, not normal. Explain uncertainty in limitations.
This is a demonstration of structured reasoning, not clinical assessment.
"""


def interpret(extraction: Extraction, client: ModelClient) -> Analysis:
    analysis = generate_validated(
        client, "Interpreter", SYSTEM_PROMPT, extraction.model_dump_json(), Analysis
    )
    expected = Counter(test.test_name for test in extraction.tests)
    actual = Counter(name for panel in analysis.panels for name in panel.tests)
    if actual != expected:
        raise PipelineError("Interpreter", "Panels must include every extracted test exactly once.")
    for finding in analysis.findings:
        names = finding.related_tests
        if len(names) != len(set(names)) or not set(names).issubset(expected):
            raise PipelineError("Interpreter", "A finding cites unknown or duplicate tests.")
    abnormal = {test.test_name for test in extraction.tests if test.status in {"low", "high"}}
    cited = {name for finding in analysis.findings for name in finding.related_tests}
    if not abnormal.issubset(cited):
        raise PipelineError("Interpreter", "Findings omitted an out-of-range result.")
    return analysis

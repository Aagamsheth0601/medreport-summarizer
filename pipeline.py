"""Reusable orchestration: returns all stages and never writes a shared output file."""

from collections.abc import Callable
from agents.communicator import communicate, render_summary
from agents.extractor import extract
from agents.interpreter import interpret
from llm import ModelClient
from samples import load_sample, verify_extraction
from schemas import Extraction, PipelineResult


def run_pipeline(sample_id: str, client: ModelClient,
                 on_progress: Callable[[str, str], None] | None = None) -> PipelineResult:
    report, expected = load_sample(sample_id)
    return run_report(sample_id, report, expected, client, on_progress)


def run_report(sample_id: str, report: str, expected: Extraction, client: ModelClient,
               on_progress: Callable[[str, str], None] | None = None) -> PipelineResult:
    """Run the three stages on a repository-owned synthetic fixture."""

    def progress(stage: str, state: str):
        if on_progress:
            on_progress(stage, state)

    progress("Extractor", "started")
    extraction = extract(report, client)
    verify_extraction(extraction, expected)
    progress("Extractor", "completed")

    progress("Interpreter", "started")
    analysis = interpret(extraction, client)
    progress("Interpreter", "completed")

    progress("Communicator", "started")
    explanation = communicate(extraction, analysis, client)
    progress("Communicator", "completed")

    return PipelineResult(
        sample_id=sample_id, model=client.model, extraction=extraction, analysis=analysis,
        explanation=explanation, summary_markdown=render_summary(explanation),
    )

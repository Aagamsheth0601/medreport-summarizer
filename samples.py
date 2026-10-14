"""Only these repository-owned synthetic reports can enter the demo pipeline."""

from pathlib import Path
from agents import PipelineError
from schemas import Extraction

SAMPLE_DIR = Path(__file__).resolve().parent / "samples"
SAMPLE_IDS = ("within-range", "mixed-patterns", "range-boundaries")


def load_sample(sample_id: str) -> tuple[str, Extraction]:
    # Validate before constructing paths: callers cannot supply uploads or traversal.
    if sample_id not in SAMPLE_IDS:
        raise PipelineError("Input", "Choose a built-in sample: " + ", ".join(SAMPLE_IDS))
    try:
        text = (SAMPLE_DIR / f"{sample_id}.txt").read_text(encoding="utf-8")
        expected = Extraction.model_validate_json(
            (SAMPLE_DIR / f"{sample_id}.expected.json").read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        raise PipelineError("Input", "Built-in sample is missing or invalid. Restore it from Git.") from exc
    if not text.strip() or len(text) > 50000:
        raise PipelineError("Input", "Built-in report is empty or too large.")
    return text, expected


def verify_extraction(actual: Extraction, expected: Extraction):
    """Known synthetic inputs give us a ground truth check, not a fake LLM result."""
    by_name = lambda result: {test.test_name: test.model_dump() for test in result.tests}
    if by_name(actual) != by_name(expected) or actual.warnings != expected.warnings:
        raise PipelineError("Extractor", "Extraction does not match the built-in sample's verified values or warnings.")

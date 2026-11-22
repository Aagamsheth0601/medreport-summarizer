"""Compare one Gemini call with MedReport's three agents on fixed synthetic fixtures."""

import argparse
from collections.abc import Callable
from pathlib import Path
import sys
from time import perf_counter
from typing import Literal, Protocol
from uuid import uuid4

from dotenv import load_dotenv
from pydantic import TypeAdapter

from agents import PipelineError
from agents.communicator import SYSTEM_PROMPT as COMMUNICATOR_PROMPT
from agents.communicator import render_summary, verify_explanations
from agents.extractor import SYSTEM_PROMPT as EXTRACTOR_PROMPT
from agents.interpreter import SYSTEM_PROMPT as INTERPRETER_PROMPT
from agents.interpreter import validate_analysis
from llm import GeminiClient, ModelClient, generate_validated
from main import save_result
from pipeline import run_report
from samples import verify_extraction
from schemas import Analysis, CommunicatorResponse, Contract, Extraction, PipelineResult, Text


ROOT = Path(__file__).resolve().parent
Mode = Literal["single-call", "three-agent"]
MODES: tuple[Mode, Mode] = ("single-call", "three-agent")
SINGLE_PROMPT = (
    "Complete all three tasks in one JSON response with extraction, analysis, and explanation. "
    "The supplied text is the only report input. Analyze your own extraction and explain "
    "your own analysis. In explanation.findings_explained, use the one-based position "
    "in analysis.findings as finding_id.\n\n"
    f"Extraction instructions:\n{EXTRACTOR_PROMPT}\n"
    f"Analysis instructions:\n{INTERPRETER_PROMPT}\n"
    f"Explanation instructions:\n{COMMUNICATOR_PROMPT}"
)


class BenchmarkCase(Contract):
    sample_id: Text
    report: Text
    expected: Extraction


class SingleCallResponse(Contract):
    extraction: Extraction
    analysis: Analysis
    explanation: CommunicatorResponse


class Attempt(Contract):
    sample_id: Text
    mode: Mode
    elapsed_ms: int
    model_calls: int
    total_tokens: int | None
    extraction_verified: bool
    error: str | None
    result: PipelineResult | None


class BenchmarkRun(Contract):
    model: Text
    attempts: list[Attempt]


class UsageClient(ModelClient, Protocol):
    last_total_tokens: int | None


class MeasuredClient:
    def __init__(self, client: UsageClient):
        self.client = client
        self.model = client.model
        self.token_counts: list[int | None] = []

    def generate(self, stage, prompt, contents, schema):
        try:
            return self.client.generate(stage, prompt, contents, schema)
        finally:
            self.token_counts.append(self.client.last_total_tokens)


def load_cases() -> list[BenchmarkCase]:
    return TypeAdapter(list[BenchmarkCase]).validate_json(
        (ROOT / "benchmark_cases.json").read_text(encoding="utf-8")
    )


def run_single(case: BenchmarkCase, client: ModelClient,
               progress: Callable[[str, str], None]) -> PipelineResult:
    response = generate_validated(
        client, "Single call", SINGLE_PROMPT, case.report, SingleCallResponse
    )
    verify_extraction(response.extraction, case.expected)
    progress("Extractor", "completed")
    analysis = validate_analysis(response.extraction, response.analysis)
    explanation = verify_explanations(response.extraction, analysis, response.explanation)
    return PipelineResult(
        sample_id=case.sample_id, model=client.model, extraction=response.extraction,
        analysis=analysis, explanation=explanation,
        summary_markdown=render_summary(explanation),
    )


def run_attempt(case: BenchmarkCase, mode: Mode, client: UsageClient) -> Attempt:
    measured = MeasuredClient(client)
    extraction_verified = False
    result: PipelineResult | None = None
    error: str | None = None

    def progress(stage: str, state: str):
        nonlocal extraction_verified
        if stage == "Extractor" and state == "completed":
            extraction_verified = True

    started = perf_counter()
    try:
        if mode == "single-call":
            result = run_single(case, measured, progress)
        else:
            result = run_report(case.sample_id, case.report, case.expected, measured, progress)
    except PipelineError as exc:
        error = str(exc)
    elapsed_ms = round((perf_counter() - started) * 1000)
    counts = measured.token_counts
    total_tokens = (
        sum(count for count in counts if count is not None)
        if counts and None not in counts else None
    )
    return Attempt(
        sample_id=case.sample_id, mode=mode, elapsed_ms=elapsed_ms, model_calls=len(counts),
        total_tokens=total_tokens, extraction_verified=extraction_verified,
        error=error, result=result,
    )


def main(argv=None) -> int:
    cases = load_cases()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=[case.sample_id for case in cases])
    parser.add_argument("--output", type=Path, help="New JSON file for measurements and outputs")
    args = parser.parse_args(argv)
    output = args.output or Path("outputs") / f"benchmark-{uuid4().hex}.json"

    load_dotenv(ROOT / ".env")
    client = None
    try:
        if output.exists():
            raise PipelineError("Output", "Output file already exists; choose a new filename.")
        client = GeminiClient()
        attempts = []
        for index, case in enumerate(cases):
            if args.case and args.case != case.sample_id:
                continue
            # Alternate the order so the same mode does not always go first.
            for mode in MODES if index % 2 == 0 else reversed(MODES):
                print(f"{case.sample_id} | {mode}: running", flush=True)
                attempt = run_attempt(case, mode, client)
                attempts.append(attempt)
                tokens = attempt.total_tokens if attempt.total_tokens is not None else "unavailable"
                print(f"  {attempt.error or 'passed'} | {attempt.elapsed_ms} ms | {tokens} tokens",
                      flush=True)
        save_result(BenchmarkRun(model=client.model, attempts=attempts), output)
        print(f"Saved {len(attempts)} attempts to {output}")
        return int(any(attempt.error for attempt in attempts))
    except PipelineError as exc:
        print(f"Benchmark stopped. {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("Benchmark output could not be saved. Check the path and disk space.", file=sys.stderr)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    sys.exit(main())

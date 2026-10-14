"""CLI adapter for the synthetic-only portfolio pipeline."""

import argparse
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4
from dotenv import load_dotenv
from agents import PipelineError
from llm import GeminiClient
from pipeline import run_pipeline
from samples import SAMPLE_IDS


def publish_output(temporary: Path, output: Path):
    # Windows rename fails if the destination exists; POSIX rename would overwrite.
    if os.name == "nt":
        os.rename(temporary, output)
    else:
        os.link(temporary, output)


def save_result(result, output: Path):
    """Publish a complete file atomically without overwriting an existing result."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output.parent,
                                         prefix=".medreport-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(result.model_dump_json(indent=2))
        publish_output(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Three-agent synthetic-report portfolio demo")
    parser.add_argument("--sample", choices=SAMPLE_IDS, default="within-range")
    parser.add_argument("--list", action="store_true", help="List built-in synthetic reports without an API call")
    parser.add_argument("--output", type=Path, help="New JSON output file; existing files are never overwritten")
    args = parser.parse_args(argv)
    if args.list:
        print("\n".join(SAMPLE_IDS))
        return 0

    load_dotenv(Path(__file__).resolve().parent / ".env")
    client = None
    try:
        output = args.output or Path("outputs") / f"{args.sample}-{uuid4().hex}.json"
        if output.exists():
            raise PipelineError("Output", "Output file already exists; choose a new filename.")
        client = GeminiClient()
        print("PORTFOLIO DEMO: synthetic reports only; AI can make mistakes.", flush=True)
        result = run_pipeline(args.sample, client, lambda stage, state: print(f"{stage}: {state}", flush=True))
        save_result(result, output)
        print(f"Saved {len(result.extraction.tests)} tests and all three agent outputs to {output}")
        return 0
    except PipelineError as exc:
        print(f"Pipeline stopped. {exc}", file=sys.stderr)
        return 1
    except OSError:
        print("Pipeline stopped. Output could not be saved; check the path, permissions, and disk space.", file=sys.stderr)
        return 1
    finally:
        if client:
            client.close()


if __name__ == "__main__":
    sys.exit(main())

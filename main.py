"""End-to-end pipeline: raw blood report text -> plain-language Markdown summary.

Run: python main.py [report_path]
"""

import sys

from colorama import Fore, Style, init as colorama_init

from agents import AgentParseError
from agents.communicator import communicate
from agents.extractor import extract
from agents.interpreter import interpret

colorama_init()

C_CYAN = Fore.CYAN
C_GREEN = Fore.GREEN
C_YELLOW = Fore.YELLOW
C_RED = Fore.RED
C_DIM = Style.DIM
C_BOLD = Style.BRIGHT
C_RESET = Style.RESET_ALL


def _banner(title: str, color: str = C_CYAN) -> None:
    line = "=" * 70
    print(f"{color}{C_BOLD}{line}{C_RESET}")
    print(f"{color}{C_BOLD}{title.center(70)}{C_RESET}")
    print(f"{color}{C_BOLD}{line}{C_RESET}")
    print()


def _step_start(n: int, agent: str, msg: str) -> None:
    print(f"{C_YELLOW}>> [{n}/3] {agent:<14}{C_RESET} {C_DIM}{msg}{C_RESET}")


def _step_done(n: int, agent: str, msg: str) -> None:
    print(f"{C_GREEN}[OK] [{n}/3] {agent:<14}{C_RESET} {msg}")
    print()


def _read_report(path: str) -> str:
    """Read a blood report from a .txt or .pdf file and return its text."""
    if path.lower().endswith(".pdf"):
        from pypdf import PdfReader

        reader = PdfReader(path)
        text = "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if not text:
            raise RuntimeError(
                f"No text could be extracted from {path}. "
                "If this is a scanned PDF, it needs OCR before this pipeline can read it."
            )
        return text
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run(report_path: str, out_path: str = "summary.md") -> None:
    _banner("MEDREPORT-SUMMARIZER PIPELINE")

    report_text = _read_report(report_path)

    _step_start(1, "Extractor", "parsing raw report into structured tests...")
    extraction = extract(report_text)
    n_tests = len(extraction.get("tests", []))
    _step_done(1, "Extractor", f"{n_tests} tests extracted")

    _step_start(2, "Interpreter", "grouping panels, assigning severity and triage...")
    analysis = interpret(extraction)
    n_panels = len(analysis.get("panels", []))
    n_findings = len(analysis.get("findings", []))
    overall = analysis.get("overall_triage", "unknown").upper()
    triage_color = {"URGENT": C_RED, "ROUTINE": C_YELLOW, "MONITOR": C_GREEN}.get(overall, C_DIM)
    _step_done(
        2,
        "Interpreter",
        f"{n_panels} panels, {n_findings} findings -- overall triage: {triage_color}{C_BOLD}{overall}{C_RESET}",
    )

    _step_start(3, "Communicator", "writing plain-language summary...")
    summary = communicate(analysis)
    _step_done(3, "Communicator", "done")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(summary)

    _banner("SUMMARY SAVED", C_GREEN)
    print(f"  {C_GREEN}->{C_RESET} {out_path}")


def _print_parse_error(err: AgentParseError) -> None:
    print()
    print(f"{C_RED}{C_BOLD}!! {err.agent} produced invalid JSON{C_RESET}")
    print(f"{C_RED}-- parse error: {err.original}{C_RESET}")
    print()
    print(f"{C_DIM}--- raw output (first 800 chars) ---{C_RESET}")
    snippet = err.raw_output[:800]
    if len(err.raw_output) > 800:
        snippet += f"\n... [truncated, full length {len(err.raw_output)} chars]"
    print(snippet)
    print(f"{C_DIM}--- end raw output ---{C_RESET}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_report.txt"
    try:
        run(path)
    except AgentParseError as e:
        _print_parse_error(e)
        sys.exit(1)

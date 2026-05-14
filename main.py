"""End-to-end pipeline: raw blood report text -> plain-language Markdown summary."""

import sys

from agents.communicator import communicate
from agents.extractor import extract
from agents.interpreter import interpret


def run(report_path: str) -> str:
    with open(report_path, "r", encoding="utf-8") as f:
        report_text = f.read()
    extraction = extract(report_text)
    analysis = interpret(extraction)
    return communicate(analysis)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_report.txt"
    print(run(path))

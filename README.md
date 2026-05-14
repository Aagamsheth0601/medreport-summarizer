# medreport-summarizer

A three-agent pipeline that turns a raw blood test report into a plain-language summary and flags items that need a doctor's attention.

## Pipeline

```
raw report text
     │
     ▼
[Extractor]   →  structured JSON of every test (value, unit, range, status)
     │
     ▼
[Interpreter] →  panels, severity, cross-test patterns, triage
     │
     ▼
[Communicator] → Markdown summary for the reader
```

Each agent is a separate API call using `gemini-2.5-flash` (free tier).

## Agents

- **Extractor** — reads the raw report and pulls every test into structured JSON (name, value, unit, reference range, low/normal/high status). No interpretation.
- **Interpreter** — groups tests into clinical panels, assigns severity to abnormals, spots cross-test patterns (e.g. HbA1c + FBS = diabetic range), and sets a triage level (monitor/routine/urgent) per finding plus overall. Conservative when uncertain.
- **Communicator** — turns the analysis into a plain-language Markdown summary: quick summary, what needs attention, what looks fine, recommended next step, disclaimer. Warm tone, no diagnosing, no false reassurance.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # then put your Gemini API key in .env
```

Get a free API key from https://aistudio.google.com/ (no card required).

## Run

```bash
python main.py sample_report.txt    # plain-text report
python main.py my_report.pdf        # text-based PDF (not scanned)
```

The agents print their progress to the terminal and the final plain-language summary is written to `summary.md`. For scanned-image PDFs, run OCR first and feed the resulting text file.

## Disclaimer

**Not a medical device. Output is informational only and not a substitute for a qualified clinician.**

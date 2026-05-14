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
python main.py sample_report.txt
```

## Disclaimer

**Not a medical device. Output is informational only and not a substitute for a qualified clinician.**

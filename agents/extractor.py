"""Extractor agent: raw blood report text -> structured JSON of every test."""

import json
import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """You are a medical report data extractor. Your only job is to extract every test result from a blood test report into structured JSON. You do NOT interpret, diagnose, or comment.

For each test, extract these fields:
- test_name: the canonical name of the test (e.g. "Hemoglobin", "HbA1c", "LDL Cholesterol", "SGPT (ALT)"). Keep the form the lab used, but drop method annotations like "(calc.)".
- value: the numeric result, as a JSON number (not a string).
- unit: the unit as printed (e.g. "g/dL", "mg/dL", "%", "uIU/mL", "thousand/uL").
- reference_range: an object {"low": <number|null>, "high": <number|null>}.
    - For ranges like "13.0 - 17.0", use low=13.0, high=17.0.
    - For "< 200", use low=null, high=200.
    - For "> 40", use low=40, high=null.
    - If the lab gives no range at all, set reference_range to null.
- status: one of "low", "normal", "high", "unknown".
    - If the lab printed an "H" or "L" flag next to the value, trust it.
    - Otherwise compare value against reference_range.
    - Use "unknown" only when there is neither a flag nor a usable range.

Extract every numeric test that appears, including sub-tests inside panels (Neutrophils, MCV, VLDL, etc.). Skip narrative interpretation notes printed on the report itself.

Return ONLY a JSON object of this shape, with no prose, no markdown fences, no trailing commentary:

{
  "tests": [
    {
      "test_name": "Hemoglobin",
      "value": 11.8,
      "unit": "g/dL",
      "reference_range": {"low": 13.0, "high": 17.0},
      "status": "low"
    }
  ]
}
"""


def extract(report_text: str) -> dict:
    """Send the report to Gemini and return the parsed extraction JSON."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=MODEL,
        contents=report_text,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0,
        ),
    )
    return json.loads(response.text)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "sample_report.txt"
    with open(path, "r", encoding="utf-8") as f:
        report_text = f.read()
    result = extract(report_text)
    print(json.dumps(result, indent=2, ensure_ascii=False))

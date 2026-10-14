# Milestone one verification

Verified on Windows with Python 3.10.2 on October 14, 2026.

## Offline checks

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q --basetemp=outputs\pytest-temp
```

Result: **58 passed**. `python -m pip check` reported no broken requirements.

Coverage includes strict number/range contracts; missing and duplicate values;
exact extraction checks; missing, repeated, and invented panel/test references;
omitted out-of-range findings; missing explanations; provider errors; timeouts;
empty/truncated responses; stopped-stage progress; output failures; and unique output files.

`main.py --list` returned the three allowed sample IDs without an API call.
Git ignore checks confirmed `.env`, `.env.local`, and generated outputs are ignored.

## Live Gemini checks

Each sample completed all three real calls with `gemini-2.5-flash`:

| Sample | Extracted tests | Result |
| --- | ---: | --- |
| within-range | 4 | Passed |
| mixed-patterns | 7 | Passed |
| range-boundaries | 5 | Passed |

The live tests exposed schema compatibility errors that were fixed before these successful runs.
Saved explanations were inspected for the synthetic framing, disclaimer, source values,
and limitations. This inspection is not a clinical accuracy assessment.

After adding the final out-of-range finding-coverage check, a follow-up live run and
one retry received HTTP 503 from Gemini at the Extractor. The application returned
a clear error and created no success file. All three earlier recorded Gemini responses
were replayed through the final pipeline and passed its validation. A replay validates
the final code against recorded outputs; it is not a new live model call.

## Scope and remaining work

- Python pipeline and CLI only. No frontend or hosting has been implemented or tested.
- Only the three built-in reports are supported.
- Schema checks and fixture matching do not prove generated prose is correct.
- No evaluation comparing three calls with a single-prompt baseline has been performed.
- Live model responses, latency, availability, and quota can vary between runs.

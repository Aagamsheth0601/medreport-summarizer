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

## Communicator coverage and Gemini migration

On November 22, 2026, fresh runs with `gemini-3.5-flash-lite` passed all three pipeline stages and their validators:

| Sample | Lab values | Findings | Explanations |
| --- | ---: | ---: | ---: |
| `within-range` | 4 | 0 | 0 |
| `mixed-patterns` | 7 | 3 | 3 |
| `range-boundaries` | 5 | 1 | 1 |

The first boundary run stopped at the Interpreter with Gemini HTTP 503 and saved no result. One manual retry passed. These checks establish coverage and schema compatibility for the three synthetic runs. Generated prose accuracy requires a separate evaluation.

## Paired synthetic benchmark

On November 22, 2026, both modes used `gemini-3.5-flash-lite` and the same held-out reports in `benchmark_cases.json`. The fixtures and scoring criteria were set before the live run.

All 74 offline tests passed on Python 3.10, including tests for the shared extraction check, failed calls, and token accounting.

| Case | Mode | Result | Elapsed | Total tokens |
| --- | --- | --- | ---: | ---: |
| Routine CBC | Single call | Passed | 6.603 s | 1,295 |
| Routine CBC | Three agents | Passed | 6.587 s | 1,788 |
| Mixed iron panel | Single call | Passed | 7.882 s | 1,632 |
| Mixed iron panel | Three agents | HTTP 503 at Extractor | 0.980 s | Unavailable |
| Cutoffs and missing range | Single call | Validation error at `extraction.tests.0` | 3.000 s | 1,618 |
| Cutoffs and missing range | Three agents | Passed | 12.386 s | 1,931 |
| Mixed iron panel, repeat | Single call | Passed | 3.963 s | 1,730 |
| Mixed iron panel, repeat | Three agents | HTTP 503 at Extractor | 1.020 s | Unavailable |

Both modes passed two of three first attempts, for different cases. Every completed attempt matched the authored extraction. On the routine CBC, the only pair with two successful runs, the three-agent mode used about 38% more tokens and the two durations were within 16 ms. The HTTP failures prevented a completed mixed-panel comparison.

Manual review of the five completed explanations, including the repeat, found one range wording issue. The three-agent cutoff run correctly classified 150 as outside the supplied range of `< 150`. Its explanation called the value above the cutoff even though it was equal to the cutoff and excluded by the strict inequality. Under the benchmark rubric, no out-of-range result or missing-range limitation was omitted from those completed outputs, and no diagnosis or treatment recommendation appeared.

This is a small first comparison. The results identify a testable prose-grounding gap and give one matched token measurement. More completed pairs and repeated runs are needed to estimate overall quality or typical latency.

## Strict cutoff regression

An offline regression reproduced incorrect above/below wording for both strict cutoff directions. The fix also covers other tests cited by the same finding, including inclusive boundaries and missing ranges. All 76 offline tests passed.

In a fresh 3.5 Flash-Lite run on `cutoffs-and-missing-range`, the three-agent trace and Markdown report both said: “Triglycerides measured 150 mg/dL, exactly at the excluded cutoff (< 150).” The single-call attempt again failed extraction validation at `extraction.tests.0`. The offline comparison exercised the shared wording fix through both modes with a valid extraction.

The public “Right on the boundary” recording was refreshed from a new Gemini 3.5 Flash-Lite run. Both strict cutoff findings use the validated wording in the overview, trace, and Markdown. The production build on Node 20.11.1 included the refreshed recording.

The other two public samples now use authentic 3.5 Flash-Lite recordings as well. The mixed-pattern sample completed a fresh run. Gemini returned HTTP 503 at the Interpreter on both new within-range attempts, so the refresh uses the earlier successful 3.5 Flash-Lite run. Both recordings passed the current validation checks before publication.

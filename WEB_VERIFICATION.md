# Milestone two verification

Verified October 14, 2026, on Windows, Python 3.10.2 and Node 20.11.1.

- **65 Python tests passed** (58 pipeline/CLI tests and 7 new API tests).
- `pip check`: no broken requirements. Vite production build passed.
- Actual HTTP health and catalogue endpoints returned the three synthetic reports.
- A browser-triggered live Gemini run completed all three agents: **7 values, 3 findings** for `mixed-patterns`.
- Verified actual progress, disabled sample selection during execution, summary and JSON downloads, values table, expandable trace, and keyboard tab navigation.
- Verified missing-key handling against the actual API. Injected browser failures checked catalogue retry, HTTP 409, expired jobs, and interrupted polling/reconnect to the same job.
- Playwright checked Overview, Lab values, and Agent trace at **390, 768, and 1280 pixels**. No page-level horizontal overflow. The mobile table has its own scroll region and visible hint.
- Screenshots were visually inspected; heading whitespace and skip-link capture issues were fixed. Final screenshots reuse the actual live result through browser route injection to avoid additional model calls.
- No hosting or deployment was performed. This is a local, single-worker application with in-memory jobs.

## Reproduce

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
Set-Location frontend
npm ci
npm run build
Set-Location ..
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Visit http://127.0.0.1:8000, choose a sample, analyze, inspect all three views, and download the results.
API tests use scripted responses, not clinical validation. Browser fault injection is verification only;
the application has no hidden fake-analysis mode.

## Local live sandbox checkpoint

Verified November 27, 2026, with Python 3.10 and Node 20.11.1.

- All 76 offline tests passed.
- Playwright switched between Recorded demo and Live Gemini at 390, 768, and 1280 px. Recorded playback made zero API requests, and live mode loaded the three samples through FastAPI.
- The browser started `range-boundaries` with HTTP 202, polled the same run ID, and displayed all three completed stages, five measurements, and the Agent trace. The result reported Gemini 3.5 Flash-Lite.
- An interrupted poll showed a recoverable error. Reconnect fetched the same run ID and sent no second start request.
- A production build made with the development flag set still played the recordings through FastAPI's static mount and made zero API requests.

## Interface redesign checkpoint

- Checked the report workspace at 390, 768, and 1280 px. Agent names fit at every width and the phone scrolls the lab table within its own region.
- Verified keyboard navigation from Overview through Agent trace and downloaded the all-stages JSON.
- Used a controlled live response to check the running-stage pulse and result reveal. Both animations honor reduced motion.
- The Node 20.11.1 production build and all 76 offline tests passed. Updated the README's desktop and mobile screenshots from that build.

# medreport-summarizer

## Scope and collaboration

- Portfolio project demonstrating three sequential LLM agents, not a clinical tool.
- Only built-in synthetic reports are accepted. Do not add arbitrary uploads or real patient data.
- Explain changes and failures to Aagam. Work in small verified milestones and checkpoint between them.
- Milestone one is the Python pipeline; milestone two adds the local React/FastAPI app. Hosting is milestone three.
- Keep the Extractor, Interpreter, and Communicator as separate model calls with explicit contracts.
- Keep secrets in ignored `.env`; run `git check-ignore .env` before committing.
- Commit milestones with a `Co-Authored-By: Codex <noreply@openai.com>` trailer.

## Development and verification

- Windows PowerShell, Python 3.10, project `.venv`.
- Install `requirements-dev.txt`; run `python -m pytest -q` from the repository root.
- In a restricted Windows sandbox, use `python -m pytest -q --basetemp=outputs/pytest-temp`.
  This directory is disposable test data; pytest clears its contents.
- Offline tests replace the network boundary, not the pipeline. They do not establish clinical accuracy.
- Live smoke tests require a valid Gemini key and may consume quota. Use only the three built-in samples.
- Preserve local validation even when the provider supports only part of a JSON Schema.
- Verify UI changes at ~390px, ~768px, and ~1280px with Playwright. Use Vite 5 for Node 20.11.1.
- Web preview: build `frontend/` with `npm ci` and `npm run build`, then run `python -m uvicorn api:app --host 127.0.0.1 --port 8000`.
- Run one Uvicorn worker. Jobs live in bounded process memory; do not deploy multiple workers without changing storage.
- API tests require local socket access on Windows, even with fake model responses, because asyncio creates an internal socket.

## Architecture

- `schemas.py`: strict Pydantic contracts, range/status rules, fixed disclaimer.
- `llm.py`: model configuration, provider schema adaptation, timeouts, safe error messages.
- `samples.py`: allowlisted reports and exact extraction checks against authored fixtures.
- `agents/`: one focused LLM call per agent; cross-stage consistency checks.
- `pipeline.py`: orchestration and progress events; returns structured results without filesystem writes.
- `main.py`: CLI, environment loading, per-run output, atomic publication without overwrites.
- `samples/`: synthetic source reports and separately inspectable expected extraction files.

## Bug log / gotchas

### Web test client compatibility and Windows sandbox
- Symptom: API tests first failed on a deprecation warning, then hung before executing requests.
- Root cause: installed Starlette expects httpx2 for tests; the sandbox blocked asyncio's internal socketpair.
- Fix: pin httpx2 in development dependencies and run API tests with local socket access. Seven API tests passed.

### Responsive polish and visible failure handling
- Symptom: a heading joined words when its line break was hidden; the skip link appeared in scrolled full-page captures.
- Root cause: missing explicit whitespace and an offscreen-only hiding technique.
- Fix: preserve whitespace and clip the skip link until keyboard focus. Add a narrow-screen table-scroll hint.
- Network failures preserve the job ID for reconnect; expired runs and busy-server responses show explicit errors.

### Model JSON can parse but still be invalid
- Symptom: missing fields, wrong types, or duplicate tests could reach the next stage.
- Root cause: the original implementation used only `json.loads()`.
- Fix: strict Pydantic validation plus exact checks against each built-in sample. Incorrect output stops the run.

### Open range boundaries lost their meaning
- Symptom: `< 200` and `<= 200` became the same numeric bounds.
- Root cause: the original schema stored only low/high values.
- Fix: retain the printed reference text and inclusive/exclusive flags; validate status at the boundary.

### Incomplete or failed responses were not handled consistently
- Symptom: empty responses could raise unrelated errors; API failures produced raw tracebacks.
- Root cause: only JSON decoding failures were caught.
- Fix: validate completion status/text, handle provider and network failures, and name the failed stage without exposing raw payloads.

### Shared summary file could overwrite a prior run
- Symptom: every CLI invocation wrote `summary.md`.
- Root cause: a shared output path in orchestration.
- Fix: orchestration returns data. CLI defaults to UUID filenames and publishes complete files without overwriting.
  Windows uses rename; POSIX uses a same-directory hard link. Unsupported filesystems fail explicitly.

### Gemini rejected strict Pydantic schemas in live testing
- Symptom: HTTP 400 for `additional_properties`, then a schema with too many constraint states.
- Root cause: the SDK's `response_schema` representation and nested size constraints exceeded provider support.
- Fix: use `response_json_schema`, omit length/count constraints only from the provider schema, and retain full local validation.

### Test discovery and sandbox temporary files
- Symptom: a helper was collected as a test, imports failed outside the repo, and two save tests failed in sandbox system-temp.
- Root cause: helper name started with `test_`, no configured Python path, and restricted temp-directory file operations.
- Fix: rename the helper, add `pytest.ini`, and use `--basetemp=outputs/pytest-temp` in the sandbox. All tests then passed.

### Findings could omit out-of-range evidence
- Symptom: a structurally valid analysis could group a test into a panel but omit it from findings.
- Root cause: panel coverage alone did not verify finding coverage.
- Fix: require every low/high test to be cited by at least one finding. This checks coverage, not prose correctness.

## Remaining limits

- Final follow-up live verification received provider HTTP 503 twice. Earlier live runs for all three samples succeeded;
  their recorded outputs passed the final validators. See `VERIFICATION.md`. Do not describe recorded replay as a new live run.

- No clinical validation. Reference ranges are illustrative, not medical advice.
- Prose correctness and one-to-one explanation semantics are not mechanically proven.
- No automatic retries; failed stages surface errors and stop. Each request has a 60-second timeout.
- The expected fixtures are never sent as replacement model answers. They check only the Extractor result locally.
- No frontend, authentication, public endpoint, or deployment in milestone one.

### Netlify portfolio mode and layout migration
- Public React demo reads `frontend/public/demo.json`: validated saved real runs, no secrets or live calls. Do not describe playback as live inference.
- Symptom: desktop analysis left empty space after moving samples to a horizontal row. Cause: inherited workspace max-width. Fix: expand analysis to full width and recheck three viewports.
- Windows sandbox preview required elevated local socket access.

## Security/deployment maintenance October 28 2026
- Added basic response hardening: framing denied, objects disabled, base URI restricted; MIME sniffing and referrer policy set.
- Bug: dependency audits identified vulnerable build tooling. Root cause: older Vite/esbuild or source-map-js lock entries. Fix: Vite 6.4.4 and patched lock dependencies; production build and npm audit pass on Node 20.11.1.

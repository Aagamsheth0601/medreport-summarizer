"""Local web adapter: start one run, then poll its real progress.

Use one Uvicorn worker: this milestone intentionally keeps jobs in process memory.
The existing pipeline stays independent of HTTP and does not write web results to disk.
"""

from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Literal
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict

from agents import PipelineError
from llm import GeminiClient
from pipeline import run_pipeline
from samples import SAMPLE_IDS, load_sample

ROOT = Path(__file__).resolve().parent
STAGES = ("Extractor", "Interpreter", "Communicator")
SAMPLE_LABELS = {
    "within-range": ("Within the ranges", "A quiet starting point", "Four values inside their supplied ranges. Explore how the agents describe a sample without over-interpreting it."),
    "mixed-patterns": ("Connecting the patterns", "Several values, one story", "Seven measurements with a mix of low, high, and within-range results. Follow the connections between them."),
    "range-boundaries": ("Right on the boundary", "The details matter", "Five values that test strict boundaries, inclusive ranges, and a missing reference range."),
}


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sample_id: Literal["within-range", "mixed-patterns", "range-boundaries"]


class RunStore:
    """Small, bounded job store with one worker and no pending-job queue."""

    def __init__(self, client_factory=GeminiClient, runner=run_pipeline, clock=monotonic):
        self.client_factory = client_factory
        self.runner = runner
        self.clock = clock
        self.lock = Lock()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="medreport")
        self.jobs = {}
        self.active = False

    def _prune(self):
        cutoff = self.clock() - 1800
        expired = [key for key, job in self.jobs.items()
                   if job["status"] != "running" and job["updated_at"] < cutoff]
        for key in expired:
            del self.jobs[key]

    def start(self, sample_id):
        with self.lock:
            self._prune()
            if self.active:
                raise HTTPException(409, "Another analysis is running. Please wait for it to finish.")
            # Keep the most recent 20 runs at most; the browser can download a result.
            if len(self.jobs) >= 20:
                del self.jobs[next(iter(self.jobs))]
            run_id = uuid4().hex
            self.jobs[run_id] = {
                "id": run_id, "sample_id": sample_id, "status": "running",
                "stages": {stage: "waiting" for stage in STAGES},
                "result": None, "error": None, "updated_at": self.clock(),
            }
            self.active = True
        try:
            self.pool.submit(self._execute, run_id, sample_id)
        except RuntimeError:
            with self.lock:
                self.active = False
                del self.jobs[run_id]
            raise HTTPException(503, "The server is shutting down. Try again after it restarts.")
        return run_id

    def _execute(self, run_id, sample_id):
        client = None

        def progress(stage, state):
            with self.lock:
                self.jobs[run_id]["stages"][stage] = state
                self.jobs[run_id]["updated_at"] = self.clock()

        try:
            client = self.client_factory()
            result = self.runner(sample_id, client, progress)
            with self.lock:
                self.jobs[run_id].update(status="completed", result=result.model_dump())
        except Exception as error:
            # Never return provider payloads, tracebacks, or credentials to a browser.
            message = str(error) if isinstance(error, PipelineError) else "The analysis stopped unexpectedly. Please try again."
            with self.lock:
                job = self.jobs[run_id]
                job.update(status="failed", error=message)
                for stage, state in job["stages"].items():
                    if state == "started":
                        job["stages"][stage] = "failed"
        finally:
            try:
                if client is not None:
                    client.close()
            finally:
                with self.lock:
                    self.jobs[run_id]["updated_at"] = self.clock()
                    self.active = False

    def get(self, run_id):
        with self.lock:
            self._prune()
            if run_id not in self.jobs:
                raise HTTPException(404, "This run expired or the server restarted. Start a new analysis.")
            snapshot = deepcopy(self.jobs[run_id])
        snapshot.pop("updated_at")
        return snapshot

    def close(self):
        self.pool.shutdown(wait=True)


def create_app(client_factory=GeminiClient, runner=run_pipeline):
    @asynccontextmanager
    async def lifespan(app):
        load_dotenv(ROOT / ".env")
        app.state.runs = RunStore(client_factory, runner)
        yield
        app.state.runs.close()

    app = FastAPI(title="MedReport portfolio API", lifespan=lifespan)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "scope": "synthetic-reports-only"}

    @app.get("/api/samples")
    def samples():
        catalogue = []
        for sample_id in SAMPLE_IDS:
            text, expected = load_sample(sample_id)
            title, subtitle, description = SAMPLE_LABELS[sample_id]
            catalogue.append(dict(id=sample_id, title=title, subtitle=subtitle,
                                  description=description, test_count=len(expected.tests), source=text))
        return catalogue

    @app.post("/api/runs", status_code=202)
    def start_run(request: RunRequest):
        return {"id": app.state.runs.start(request.sample_id)}

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        return app.state.runs.get(run_id)

    # After `npm run build`, one Python process can also serve the web interface.
    # During development Vite proxies /api to this server; no broad CORS rule is needed.
    build = ROOT / "frontend" / "dist"
    if build.is_dir():
        app.mount("/", StaticFiles(directory=build, html=True), name="frontend")
    return app


app = create_app()

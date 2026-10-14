from threading import Event
from time import monotonic, sleep
from unittest.mock import Mock

from fastapi.testclient import TestClient

from agents import PipelineError
from api import RunStore, create_app
from test_pipeline import FakeClient, responses_for


def fake_client():
    client = FakeClient(responses_for("mixed-patterns"))
    client.close = Mock()
    return client


def wait_for_run(client, run_id):
    deadline = monotonic() + 3
    while monotonic() < deadline:
        response = client.get(f"/api/runs/{run_id}")
        response.raise_for_status()
        if response.json()["status"] != "running":
            return response.json()
        sleep(0.01)
    raise AssertionError("Test worker did not finish")


def test_catalogue_and_health_need_no_key():
    factory = Mock(side_effect=AssertionError("No model call expected"))
    with TestClient(create_app(factory)) as client:
        assert client.get("/api/health").json()["scope"] == "synthetic-reports-only"
        samples = client.get("/api/samples").json()
        assert len(samples) == 3
        assert [s["test_count"] for s in samples] == [4, 7, 5]
        assert all("SYNTHETIC" in s["source"] for s in samples)
    factory.assert_not_called()


def test_http_run_uses_real_pipeline_with_fake_network():
    with TestClient(create_app(fake_client)) as client:
        response = client.post("/api/runs", json={"sample_id": "mixed-patterns"})
        assert response.status_code == 202
        run = wait_for_run(client, response.json()["id"])
        assert run["status"] == "completed"
        assert all(state == "completed" for state in run["stages"].values())
        assert len(run["result"]["extraction"]["tests"]) == 7


def test_reject_uploads_and_unknown_ids_before_model_call():
    factory = Mock()
    with TestClient(create_app(factory)) as client:
        for body in ({"sample_id": "../../.env"}, {"sample_id": "mixed-patterns", "text": "patient report"}, {}):
            assert client.post("/api/runs", json=body).status_code == 422
        assert client.post("/api/uploads", content=b"anything").status_code in (404, 405)
    factory.assert_not_called()


def test_configuration_error_is_visible_and_releases_slot():
    factory = Mock(side_effect=PipelineError("Configuration", "Set GEMINI_API_KEY in your ignored .env file."))
    with TestClient(create_app(factory)) as client:
        for _ in range(2):
            response = client.post("/api/runs", json={"sample_id": "mixed-patterns"})
            run = wait_for_run(client, response.json()["id"])
            assert run["status"] == "failed"
            assert "GEMINI_API_KEY" in run["error"]
            assert run["result"] is None


def test_unexpected_errors_are_sanitized():
    factory = Mock(side_effect=RuntimeError("SECRET-PROVIDER-PAYLOAD"))
    with TestClient(create_app(factory)) as client:
        run_id = client.post("/api/runs", json={"sample_id": "mixed-patterns"}).json()["id"]
        run = wait_for_run(client, run_id)
        assert "SECRET" not in run["error"]
        assert run["status"] == "failed"


def test_one_run_at_a_time_and_live_progress():
    release, started = Event(), Event()

    def runner(sample_id, model, progress):
        progress("Extractor", "started")
        started.set()
        assert release.wait(3)
        raise PipelineError("Extractor", "Gemini quota reached.")

    try:
        with TestClient(create_app(fake_client, runner)) as client:
            run_id = client.post("/api/runs", json={"sample_id": "mixed-patterns"}).json()["id"]
            assert started.wait(3)
            assert client.get(f"/api/runs/{run_id}").json()["stages"]["Extractor"] == "started"
            assert client.post("/api/runs", json={"sample_id": "within-range"}).status_code == 409
            release.set()
            run = wait_for_run(client, run_id)
            assert run["stages"]["Extractor"] == "failed"
            assert run["stages"]["Interpreter"] == "waiting"
    finally:
        release.set()


def test_missing_or_expired_run():
    with TestClient(create_app(fake_client)) as client:
        assert client.get("/api/runs/missing").status_code == 404
        run_id = client.post("/api/runs", json={"sample_id": "mixed-patterns"}).json()["id"]
        wait_for_run(client, run_id)
        client.app.state.runs.clock = lambda: monotonic() + 1801
        assert client.get(f"/api/runs/{run_id}").status_code == 404

import json
from unittest.mock import Mock
import main
from agents import PipelineError
from test_pipeline import FakeClient, responses_for


def test_list_requires_no_credentials(monkeypatch, capsys):
    monkeypatch.setattr(main, "GeminiClient", Mock(side_effect=AssertionError("No network allowed")))
    assert main.main(["--list"]) == 0
    assert "range-boundaries" in capsys.readouterr().out


def test_success_saves_all_stages(monkeypatch, tmp_path):
    client = FakeClient(responses_for("within-range"))
    client.close = Mock()
    monkeypatch.setattr(main, "GeminiClient", lambda: client)
    output = tmp_path / "result.json"
    assert main.main(["--output", str(output)]) == 0
    saved = json.loads(output.read_text(encoding="utf-8"))
    assert {"extraction", "analysis", "explanation", "summary_markdown"} <= saved.keys()
    client.close.assert_called_once()


def test_stage_failure_writes_no_success_file(monkeypatch, tmp_path, capsys):
    client = FakeClient([PipelineError("Extractor", "Quota exhausted")])
    client.close = Mock()
    monkeypatch.setattr(main, "GeminiClient", lambda: client)
    output = tmp_path / "result.json"
    assert main.main(["--output", str(output)]) == 1
    assert not output.exists()
    assert "Extractor: Quota exhausted" in capsys.readouterr().err
    client.close.assert_called_once()


def test_existing_output_is_preserved_before_api_call(monkeypatch, tmp_path):
    output = tmp_path / "result.json"
    output.write_text("previous result")
    monkeypatch.setattr(main, "GeminiClient", Mock(side_effect=AssertionError("No network allowed")))
    assert main.main(["--output", str(output)]) == 1
    assert output.read_text() == "previous result"


def test_save_failure_leaves_no_partial_file(monkeypatch, tmp_path, capsys):
    client = FakeClient(responses_for("within-range"))
    client.close = Mock()
    monkeypatch.setattr(main, "GeminiClient", lambda: client)
    monkeypatch.setattr(main, "publish_output", Mock(side_effect=OSError("disk full")))
    output = tmp_path / "result.json"
    assert main.main(["--output", str(output)]) == 1
    assert not list(tmp_path.iterdir())
    assert "could not be saved" in capsys.readouterr().err


def test_default_outputs_are_unique(monkeypatch, tmp_path):
    def make_client():
        client = FakeClient(responses_for("within-range"))
        client.close = Mock()
        return client
    monkeypatch.setattr(main, "GeminiClient", make_client)
    monkeypatch.chdir(tmp_path)
    assert main.main([]) == 0
    assert main.main([]) == 0
    assert len(list((tmp_path / "outputs").glob("*.json"))) == 2

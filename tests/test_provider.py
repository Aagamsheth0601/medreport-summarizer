from types import SimpleNamespace
from unittest.mock import Mock
import httpx
import pytest
from google.genai import errors, types
from agents import PipelineError
from llm import GeminiClient, provider_schema
from schemas import Extraction


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")
    sdk = Mock()
    monkeypatch.setattr("llm.genai.Client", Mock(return_value=sdk))
    return GeminiClient()


def test_missing_key_is_actionable(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(PipelineError, match="GEMINI_API_KEY"):
        GeminiClient()


@pytest.mark.parametrize("code,phrase", [(400, "schema"), (401, "Authentication"),
    (403, "Access denied"), (404, "Model unavailable"), (429, "quota"), (503, "failed")])
def test_provider_errors_do_not_leak_payload(client, code, phrase):
    client.client.models.generate_content.side_effect = errors.APIError(code, {"message": "SECRET-PAYLOAD"})
    with pytest.raises(PipelineError, match=phrase) as caught:
        client.generate("Extractor", "prompt", "sample", Extraction)
    assert "SECRET-PAYLOAD" not in str(caught.value)


@pytest.mark.parametrize("error,phrase", [
    (httpx.ReadTimeout("secret endpoint"), "timed out"),
    (httpx.ConnectError("secret endpoint"), "connection"),
])
def test_transport_failure(client, error, phrase):
    client.client.models.generate_content.side_effect = error
    with pytest.raises(PipelineError, match=phrase):
        client.generate("Extractor", "prompt", "sample", Extraction)


@pytest.mark.parametrize("finish,text", [(types.FinishReason.MAX_TOKENS, "{}"),
    (types.FinishReason.SAFETY, ""), (types.FinishReason.STOP, None),
    (types.FinishReason.STOP, " ")])
def test_incomplete_or_empty_response(client, finish, text):
    client.client.models.generate_content.return_value = SimpleNamespace(
        candidates=[SimpleNamespace(finish_reason=finish)], text=text)
    with pytest.raises(PipelineError):
        client.generate("Extractor", "prompt", "sample", Extraction)


def test_structured_schema_and_close(client):
    client.client.models.generate_content.return_value = SimpleNamespace(
        candidates=[SimpleNamespace(finish_reason=types.FinishReason.STOP)], text="{}")
    assert client.generate("Extractor", "prompt", "sample", Extraction) == "{}"
    config = client.client.models.generate_content.call_args.kwargs["config"]
    assert config.response_json_schema == provider_schema(Extraction)
    assert config.response_schema is None
    assert "maxItems" not in str(config.response_json_schema)
    assert "maxItems" in str(Extraction.model_json_schema())
    client.close()
    client.client.close.assert_called_once()

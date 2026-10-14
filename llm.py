"""The only network boundary; tests replace it with a deterministic fake."""

import os
from typing import Protocol
import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError
from agents import PipelineError


class ModelClient(Protocol):
    model: str

    def generate(self, stage: str, prompt: str, contents: str, schema: type[BaseModel]) -> str: ...


def provider_schema(schema: type[BaseModel]) -> dict:
    """Keep types/required fields; enforce size limits locally to avoid Gemini state limits."""
    def simplify(value):
        if isinstance(value, dict):
            return {key: simplify(item) for key, item in value.items()
                    if key not in {"minLength", "maxLength", "minItems", "maxItems"}}
        if isinstance(value, list):
            return [simplify(item) for item in value]
        return value
    return simplify(schema.model_json_schema())


class GeminiClient:
    def __init__(self):
        key = os.getenv("GEMINI_API_KEY", "").strip()
        if not key:
            raise PipelineError("Configuration", "Set GEMINI_API_KEY in your ignored .env file.")
        self.model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
        if not self.model:
            raise PipelineError("Configuration", "GEMINI_MODEL must not be blank.")
        self.client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(
                timeout=60000, retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )

    def close(self):
        self.client.close()

    def generate(self, stage: str, prompt: str, contents: str, schema: type[BaseModel]) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model, contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=prompt, response_mime_type="application/json",
                    response_json_schema=provider_schema(schema),
                    temperature=0, max_output_tokens=8192,
                ),
            )
        except errors.APIError as exc:
            message = {
                400: "Provider rejected the request. Check model and schema compatibility.",
                401: "Authentication failed. Check your API key.",
                403: "Access denied. Check your API key and model permissions.",
                404: "Model unavailable. Set GEMINI_MODEL to an available model.",
                429: "Gemini quota or rate limit reached. Try again later or check quota.",
            }.get(exc.code, f"Gemini request failed (HTTP {exc.code}). Try again later.")
            raise PipelineError(stage, message) from exc
        except httpx.TimeoutException as exc:
            raise PipelineError(stage, "Gemini request timed out. Try again later.") from exc
        except httpx.RequestError as exc:
            raise PipelineError(stage, "Cannot reach Gemini. Check your connection.") from exc
        candidates = response.candidates or []
        if not candidates or candidates[0].finish_reason != types.FinishReason.STOP:
            raise PipelineError(stage, "Gemini response was blocked or incomplete; no result was saved.")
        if not response.text or not response.text.strip():
            raise PipelineError(stage, "Gemini returned an empty response.")
        return response.text


def generate_validated(client: ModelClient, stage: str, prompt: str, contents: str, schema):
    raw = client.generate(stage, prompt, contents, schema)
    if not isinstance(raw, str) or not raw.strip():
        raise PipelineError(stage, "Model returned an empty response.")
    try:
        return schema.model_validate_json(raw)
    except ValidationError as exc:
        locations = [".".join(map(str, error["loc"])) or "root" for error in exc.errors()[:3]]
        raise PipelineError(stage, "Invalid model output at: " + ", ".join(locations)) from exc

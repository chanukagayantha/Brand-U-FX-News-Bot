import json
from unittest.mock import MagicMock

from google.genai import errors as genai_errors

from src.providers.gemini_backend import GeminiBackend

SCHEMA = {"type": "object", "properties": {}}


def make_response(payload: dict, finish_reason: str = "STOP"):
    candidate = MagicMock()
    candidate.finish_reason = finish_reason
    response = MagicMock()
    response.candidates = [candidate]
    response.text = json.dumps(payload)
    return response


def test_generate_well_formed_response():
    client = MagicMock()
    payload = {"relevant": True, "direction": "bullish"}
    client.models.generate_content.return_value = make_response(payload)

    backend = GeminiBackend(client=client, model="gemini-2.5-flash")
    result = backend.generate("system prompt", "user content", SCHEMA)

    assert result == json.dumps(payload)

    _, kwargs = client.models.generate_content.call_args
    assert kwargs["model"] == "gemini-2.5-flash"
    assert kwargs["contents"] == "user content"
    config = kwargs["config"]
    assert config.system_instruction == "system prompt"
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == SCHEMA
    assert config.thinking_config.thinking_budget == 0


def test_generate_handles_blocked_finish_reason():
    client = MagicMock()
    client.models.generate_content.return_value = make_response({}, finish_reason="SAFETY")

    backend = GeminiBackend(client=client, model="gemini-2.5-flash")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_max_tokens_truncation():
    client = MagicMock()
    client.models.generate_content.return_value = make_response({}, finish_reason="MAX_TOKENS")

    backend = GeminiBackend(client=client, model="gemini-2.5-flash")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_empty_candidates():
    client = MagicMock()
    response = MagicMock()
    response.candidates = []
    response.text = None
    client.models.generate_content.return_value = response

    backend = GeminiBackend(client=client, model="gemini-2.5-flash")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_rate_limit_error():
    client = MagicMock()
    client.models.generate_content.side_effect = genai_errors.ClientError(
        code=429, response_json={"message": "rate limited"}
    )

    backend = GeminiBackend(client=client, model="gemini-2.5-flash")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_other_client_error():
    client = MagicMock()
    client.models.generate_content.side_effect = genai_errors.ClientError(
        code=400, response_json={"message": "bad request"}
    )

    backend = GeminiBackend(client=client, model="gemini-2.5-flash")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_server_error():
    client = MagicMock()
    client.models.generate_content.side_effect = genai_errors.ServerError(
        code=500, response_json={"message": "internal error"}
    )

    backend = GeminiBackend(client=client, model="gemini-2.5-flash")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_unexpected_transport_error():
    client = MagicMock()
    client.models.generate_content.side_effect = ConnectionError("boom")

    backend = GeminiBackend(client=client, model="gemini-2.5-flash")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None

import json
from unittest.mock import MagicMock

import anthropic

from src.providers.claude_backend import ClaudeBackend

SCHEMA = {"type": "object", "properties": {}}


def make_text_response(payload: dict, stop_reason: str = "end_turn"):
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [block]
    response.stop_reason = stop_reason
    return response


def test_generate_well_formed_response():
    client = MagicMock()
    payload = {"relevant": True, "direction": "bullish"}
    client.messages.create.return_value = make_text_response(payload)

    backend = ClaudeBackend(client=client, model="claude-sonnet-5")
    result = backend.generate("system prompt", "user content", SCHEMA)

    assert result == json.dumps(payload)

    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-sonnet-5"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["output_config"]["format"]["schema"] == SCHEMA
    assert kwargs["system"][0]["text"] == "system prompt"
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["messages"] == [{"role": "user", "content": "user content"}]


def test_generate_handles_refusal():
    client = MagicMock()
    response = MagicMock()
    response.stop_reason = "refusal"
    response.content = []
    client.messages.create.return_value = response

    backend = ClaudeBackend(client=client, model="claude-sonnet-5")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_max_tokens_truncation():
    client = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "{}"
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "max_tokens"
    client.messages.create.return_value = response

    backend = ClaudeBackend(client=client, model="claude-sonnet-5")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_rate_limit_error():
    client = MagicMock()
    client.messages.create.side_effect = anthropic.RateLimitError(
        message="rate limited", response=MagicMock(status_code=429), body=None
    )

    backend = ClaudeBackend(client=client, model="claude-sonnet-5")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_connection_error():
    client = MagicMock()
    client.messages.create.side_effect = anthropic.APIConnectionError(request=MagicMock())

    backend = ClaudeBackend(client=client, model="claude-sonnet-5")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None


def test_generate_handles_api_status_error():
    client = MagicMock()
    client.messages.create.side_effect = anthropic.APIStatusError(
        message="server error", response=MagicMock(status_code=500), body=None
    )

    backend = ClaudeBackend(client=client, model="claude-sonnet-5")
    result = backend.generate("system", "user", SCHEMA)

    assert result is None

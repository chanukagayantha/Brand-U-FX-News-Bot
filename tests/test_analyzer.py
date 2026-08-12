import json
from unittest.mock import MagicMock

import anthropic
import pytest

from src.analyzer import GoldNewsAnalyzer
from src.models import NewsItem


def make_item():
    return NewsItem(
        url="https://example.com/a",
        title="Fed signals rate cuts",
        summary="The Fed hinted at rate cuts amid cooling inflation.",
        source="Test Source",
        published_at="2026-01-01",
        content_hash="hash-a",
    )


def make_text_response(payload: dict, stop_reason: str = "end_turn"):
    block = MagicMock()
    block.type = "text"
    block.text = json.dumps(payload)
    response = MagicMock()
    response.content = [block]
    response.stop_reason = stop_reason
    return response


def test_analyze_news_item_well_formed_json():
    client = MagicMock()
    payload = {
        "relevant": True,
        "direction": "bullish",
        "impact_level": "medium",
        "confidence": 0.8,
        "summary": "Gold rises on dovish Fed signal.",
        "reasoning": "Lower expected real rates support gold.",
    }
    client.messages.create.return_value = make_text_response(payload)

    analyzer = GoldNewsAnalyzer(client=client, model="claude-sonnet-5")
    result = analyzer.analyze_news_item(make_item())

    assert result is not None
    assert result.relevant is True
    assert result.direction == "bullish"
    assert result.impact_level == "medium"
    assert result.model == "claude-sonnet-5"

    _, kwargs = client.messages.create.call_args
    assert kwargs["model"] == "claude-sonnet-5"
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}


def test_analyze_handles_refusal():
    client = MagicMock()
    response = MagicMock()
    response.stop_reason = "refusal"
    response.content = []
    client.messages.create.return_value = response

    analyzer = GoldNewsAnalyzer(client=client, model="claude-sonnet-5")
    result = analyzer.analyze_news_item(make_item())

    assert result is None


def test_analyze_handles_malformed_json():
    client = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "not valid json"
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    client.messages.create.return_value = response

    analyzer = GoldNewsAnalyzer(client=client, model="claude-sonnet-5")
    result = analyzer.analyze_news_item(make_item())

    assert result is None


def test_analyze_handles_rate_limit_error():
    client = MagicMock()
    client.messages.create.side_effect = anthropic.RateLimitError(
        message="rate limited", response=MagicMock(status_code=429), body=None
    )

    analyzer = GoldNewsAnalyzer(client=client, model="claude-sonnet-5")
    result = analyzer.analyze_news_item(make_item())

    assert result is None


def test_analyze_handles_max_tokens_truncation():
    client = MagicMock()
    block = MagicMock()
    block.type = "text"
    block.text = "{}"
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "max_tokens"
    client.messages.create.return_value = response

    analyzer = GoldNewsAnalyzer(client=client, model="claude-sonnet-5")
    result = analyzer.analyze_news_item(make_item())

    assert result is None

import json
from typing import Optional

from src.analyzer import ANALYSIS_SCHEMA, SYSTEM_PROMPT, GoldNewsAnalyzer
from src.models import CalendarEvent, NewsItem
from src.providers.base import AnalyzerBackend


class FakeBackend(AnalyzerBackend):
    def __init__(self, return_value: Optional[str] = None, model: str = "fake-model"):
        self.model = model
        self.return_value = return_value
        self.calls = []

    def generate(self, system_prompt, user_content, schema):
        self.calls.append((system_prompt, user_content, schema))
        return self.return_value


def make_item():
    return NewsItem(
        url="https://example.com/a",
        title="Fed signals rate cuts",
        summary="The Fed hinted at rate cuts amid cooling inflation.",
        source="Test Source",
        published_at="2026-01-01",
        content_hash="hash-a",
    )


def make_payload():
    return {
        "relevant": True,
        "direction": "bullish",
        "impact_level": "medium",
        "confidence": 0.8,
        "summary": "Gold rises on dovish Fed signal.",
        "reasoning": "Lower expected real rates support gold.",
    }


def test_analyze_news_item_well_formed_json():
    backend = FakeBackend(return_value=json.dumps(make_payload()), model="fake-model")
    analyzer = GoldNewsAnalyzer(backend=backend)

    result = analyzer.analyze_news_item(make_item())

    assert result is not None
    assert result.relevant is True
    assert result.direction == "bullish"
    assert result.impact_level == "medium"
    assert result.model == "fake-model"


def test_analyze_news_item_passes_prompt_and_schema_through_unchanged():
    backend = FakeBackend(return_value=json.dumps(make_payload()))
    analyzer = GoldNewsAnalyzer(backend=backend)

    analyzer.analyze_news_item(make_item())

    assert len(backend.calls) == 1
    system_prompt, user_content, schema = backend.calls[0]
    assert system_prompt == SYSTEM_PROMPT
    assert schema == ANALYSIS_SCHEMA
    assert "Fed signals rate cuts" in user_content
    assert "Type: News article" in user_content


def test_analyze_calendar_event_builds_expected_content():
    backend = FakeBackend(return_value=json.dumps(make_payload()))
    analyzer = GoldNewsAnalyzer(backend=backend)
    event = CalendarEvent(
        event_key="key-1",
        title="CPI m/m",
        country="USD",
        event_date="2026-01-14T13:30:00-05:00",
        source_impact="High",
        forecast="0.3%",
        previous="0.2%",
        actual=None,
    )

    analyzer.analyze_calendar_event(event)

    _, user_content, _ = backend.calls[0]
    assert "Type: Economic calendar event" in user_content
    assert "CPI m/m" in user_content
    assert "not yet released" in user_content


def test_analyze_returns_none_when_backend_fails():
    backend = FakeBackend(return_value=None)
    analyzer = GoldNewsAnalyzer(backend=backend)

    result = analyzer.analyze_news_item(make_item())

    assert result is None


def test_analyze_handles_malformed_json():
    backend = FakeBackend(return_value="not valid json")
    analyzer = GoldNewsAnalyzer(backend=backend)

    result = analyzer.analyze_news_item(make_item())

    assert result is None

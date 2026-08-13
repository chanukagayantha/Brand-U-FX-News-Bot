from unittest.mock import MagicMock, patch

from src.config import Config
from src.models import AnalysisResult, CalendarEvent, NewsItem
from src.pipeline import Pipeline


def make_config():
    return Config(
        anthropic_api_key="test-key",
        rss_feeds=["https://example.com/feed.xml"],
        calendar_url="https://example.com/calendar.json",
    )


def make_analysis(relevant=True, direction="bullish"):
    return AnalysisResult(
        relevant=relevant,
        direction=direction,
        impact_level="medium",
        confidence=0.8,
        summary="summary",
        reasoning="reasoning",
        model="claude-sonnet-5",
        raw_response="{}",
    )


@patch("src.pipeline.fetch_calendar_events")
@patch("src.pipeline.fetch_rss_items")
def test_pipeline_analyzes_relevant_news_only(mock_fetch_rss, mock_fetch_cal, storage):
    mock_fetch_rss.return_value = [
        NewsItem(
            url="https://example.com/gold",
            title="Fed signals rate cuts, gold rallies",
            summary="Gold up on dovish Fed",
            source="Test",
            published_at="2026-01-01",
            content_hash="h1",
        ),
        NewsItem(
            url="https://example.com/bakery",
            title="Local bakery wins award",
            summary="Nothing macro related here",
            source="Test",
            published_at="2026-01-01",
            content_hash="h2",
        ),
    ]
    mock_fetch_cal.return_value = []

    analyzer = MagicMock()
    analyzer.analyze_news_item.return_value = make_analysis()

    pipeline = Pipeline(make_config(), storage, analyzer)
    stats = pipeline.run_once()

    assert stats.news_fetched == 2
    assert stats.news_prefiltered_in == 1
    assert stats.news_analyzed == 1
    # The irrelevant bakery item should never reach the analyzer.
    analyzer.analyze_news_item.assert_called_once()


@patch("src.pipeline.fetch_calendar_events")
@patch("src.pipeline.fetch_rss_items")
def test_pipeline_dedupes_across_runs(mock_fetch_rss, mock_fetch_cal, storage):
    item = NewsItem(
        url="https://example.com/gold",
        title="Fed signals rate cuts, gold rallies",
        summary="Gold up on dovish Fed",
        source="Test",
        published_at="2026-01-01",
        content_hash="h1",
    )
    mock_fetch_rss.return_value = [item]
    mock_fetch_cal.return_value = []

    analyzer = MagicMock()
    analyzer.analyze_news_item.return_value = make_analysis()

    pipeline = Pipeline(make_config(), storage, analyzer)
    pipeline.run_once()
    stats_second_run = pipeline.run_once()

    # Same item fetched again on the second poll must not be re-analyzed.
    assert stats_second_run.news_analyzed == 0
    analyzer.analyze_news_item.assert_called_once()


@patch("src.pipeline.fetch_calendar_events")
@patch("src.pipeline.fetch_rss_items")
def test_pipeline_calendar_pending_then_released(mock_fetch_rss, mock_fetch_cal, storage):
    mock_fetch_rss.return_value = []
    pending = CalendarEvent(
        event_key="key-1",
        title="CPI m/m",
        country="USD",
        event_date="2026-01-14T13:30:00-05:00",
        source_impact="High",
        forecast="0.3%",
        previous="0.2%",
        actual=None,
    )
    mock_fetch_cal.return_value = [pending]

    analyzer = MagicMock()
    analyzer.analyze_calendar_event.return_value = make_analysis()

    pipeline = Pipeline(make_config(), storage, analyzer)
    stats_first = pipeline.run_once()
    assert stats_first.calendar_analyzed == 1

    # Unchanged repoll: no re-analysis.
    stats_repoll = pipeline.run_once()
    assert stats_repoll.calendar_analyzed == 0

    released = CalendarEvent(
        event_key="key-1",
        title="CPI m/m",
        country="USD",
        event_date="2026-01-14T13:30:00-05:00",
        source_impact="High",
        forecast="0.3%",
        previous="0.2%",
        actual="0.4%",
    )
    mock_fetch_cal.return_value = [released]
    stats_released = pipeline.run_once()
    assert stats_released.calendar_analyzed == 1

    assert analyzer.analyze_calendar_event.call_count == 2

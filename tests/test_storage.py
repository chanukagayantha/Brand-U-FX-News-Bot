from src.models import AnalysisResult, CalendarEvent, NewsItem


def make_news_item(url="https://example.com/a", title="Gold rallies"):
    return NewsItem(
        url=url,
        title=title,
        summary="Gold rallies on Fed comments",
        source="Test Source",
        published_at="2026-01-01",
        content_hash="hash-a",
    )


def make_analysis(relevant=True):
    return AnalysisResult(
        relevant=relevant,
        direction="bullish",
        impact_level="medium",
        confidence=0.8,
        summary="Gold rises on dovish Fed.",
        reasoning="Lower real rates expected.",
        model="claude-sonnet-5",
        raw_response="{}",
    )


def test_news_item_dedupe_by_url(storage):
    item = make_news_item()
    assert storage.news_item_exists(item.url) is False

    storage.save_news_item(item, prefilter_matched=True, matched_keywords="gold, fed")
    assert storage.news_item_exists(item.url) is True


def test_save_news_analysis_updates_status(storage):
    item = make_news_item()
    item_id = storage.save_news_item(item, prefilter_matched=True, matched_keywords="gold")
    storage.save_news_analysis(item_id, make_analysis())

    row = storage._conn.execute(
        "SELECT analysis_status FROM news_items WHERE id = ?", (item_id,)
    ).fetchone()
    assert row["analysis_status"] == "analyzed"


def test_calendar_event_first_sighting_triggers_analysis(storage):
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
    row_id, should_analyze = storage.upsert_calendar_event(event)
    assert should_analyze is True
    assert row_id is not None


def test_calendar_event_unchanged_repoll_does_not_reanalyze(storage):
    event = CalendarEvent(
        event_key="key-2",
        title="CPI m/m",
        country="USD",
        event_date="2026-01-14T13:30:00-05:00",
        source_impact="High",
        forecast="0.3%",
        previous="0.2%",
        actual=None,
    )
    storage.upsert_calendar_event(event)  # first sighting
    row_id, should_analyze = storage.upsert_calendar_event(event)  # unchanged repoll

    assert should_analyze is False
    assert row_id is not None


def test_calendar_event_release_triggers_reanalysis_exactly_once(storage):
    pending = CalendarEvent(
        event_key="key-3",
        title="CPI m/m",
        country="USD",
        event_date="2026-01-14T13:30:00-05:00",
        source_impact="High",
        forecast="0.3%",
        previous="0.2%",
        actual=None,
    )
    storage.upsert_calendar_event(pending)  # first sighting, should_analyze=True

    released = CalendarEvent(
        event_key="key-3",
        title="CPI m/m",
        country="USD",
        event_date="2026-01-14T13:30:00-05:00",
        source_impact="High",
        forecast="0.3%",
        previous="0.2%",
        actual="0.4%",
    )
    _, should_analyze_on_release = storage.upsert_calendar_event(released)
    assert should_analyze_on_release is True

    # Polling again with the same released data must not trigger a third analysis.
    _, should_analyze_again = storage.upsert_calendar_event(released)
    assert should_analyze_again is False


def test_unsent_analyses_seam(storage):
    item = make_news_item()
    item_id = storage.save_news_item(item, prefilter_matched=True, matched_keywords="gold")
    storage.save_news_analysis(item_id, make_analysis())

    unsent = storage.get_unsent_analyses()
    assert len(unsent) == 1

    storage.mark_distributed(unsent[0]["id"])
    assert storage.get_unsent_analyses() == []

"""Pure formatting helpers — the seam a future distribution layer (Telegram/email) reuses."""

from __future__ import annotations

from src.models import AnalysisResult, CalendarEvent, NewsItem

_DIRECTION_EMOJI = {"bullish": "^", "bearish": "v", "neutral": "-"}


def format_news_output(item: NewsItem, result: AnalysisResult) -> str:
    arrow = _DIRECTION_EMOJI.get(result.direction, "-")
    return (
        f"[{arrow} {result.direction.upper()} | impact={result.impact_level} | "
        f"confidence={result.confidence:.2f}]\n"
        f"{item.source} — {item.published_at or 'unknown time'}\n"
        f"{item.title}\n"
        f"Summary: {result.summary}\n"
        f"Why: {result.reasoning}"
    )


def format_calendar_output(event: CalendarEvent, trigger: str, result: AnalysisResult) -> str:
    arrow = _DIRECTION_EMOJI.get(result.direction, "-")
    stage = "released" if trigger == "released" else "upcoming"
    return (
        f"[{arrow} {result.direction.upper()} | impact={result.impact_level} | "
        f"confidence={result.confidence:.2f}]\n"
        f"{event.country} calendar event ({stage}) — {event.event_date}\n"
        f"{event.title} (forecast={event.forecast or 'n/a'}, "
        f"previous={event.previous or 'n/a'}, actual={event.actual or 'n/a'})\n"
        f"Summary: {result.summary}\n"
        f"Why: {result.reasoning}"
    )

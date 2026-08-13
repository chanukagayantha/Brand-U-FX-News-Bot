"""Provider-agnostic gold market impact analysis: builds prompts, calls a backend, parses JSON."""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.models import AnalysisResult, CalendarEvent, NewsItem
from src.providers.base import AnalyzerBackend

logger = logging.getLogger(__name__)

_MAX_SUMMARY_CHARS = 1500

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "relevant": {"type": "boolean"},
        "direction": {"type": "string", "enum": ["bullish", "bearish", "neutral"]},
        "impact_level": {"type": "string", "enum": ["high", "medium", "low", "none"]},
        "confidence": {"type": "number"},
        "summary": {"type": "string"},
        "reasoning": {"type": "string"},
    },
    "required": ["relevant", "direction", "impact_level", "confidence", "summary", "reasoning"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """\
You are a gold market (XAU/USD) analyst. Your job is to read a single news item or
economic-calendar event and judge its likely near-term impact on the price of gold.

Gold's core price drivers, in rough order of importance:
- Real interest rates and the US dollar (DXY): gold is priced in dollars and pays no
  yield, so it moves inversely with real rates and the dollar. Hawkish Fed commentary,
  rising real yields, or a strengthening dollar are typically bearish for gold; dovish
  commentary, falling real yields, or a weakening dollar are typically bullish.
- Safe-haven demand: geopolitical conflict, financial-system stress, sanctions, and
  sovereign-risk events push capital into gold (bullish), while broad risk-on sentiment
  pulls capital out of gold (bearish).
- Inflation expectations: rising inflation expectations are generally bullish for gold
  as a store of value, though this effect is secondary to the real-rate channel above.
- Central-bank gold buying/selling: sustained official-sector demand is a slower-moving
  but persistent bullish factor.

For scheduled economic-calendar events (CPI, PCE, NFP, GDP, Fed rate decisions, etc.),
what matters is the SURPRISE relative to the forecast/consensus, not the absolute level.
A CPI print that comes in below forecast is disinflationary and typically dovish/bullish
for gold even if the absolute number is still "high." When "actual" is not yet available,
assess the event's POTENTIAL impact if it surprises meaningfully; when "actual" is
available, assess the REALIZED impact of actual vs. forecast/previous.

Worked examples to calibrate your output:
1. Headline: "US CPI rises 0.2% MoM, below the 0.3% forecast" (calendar event, actual
   available). This is a downside inflation surprise -> lower real-rate expectations ->
   bullish for gold. direction="bullish", impact_level depends on the size of the miss
   (a small miss like this is typically "medium").
2. Headline: "Fed's Powell: rates will stay higher for longer as inflation proves
   sticky" (news item). Hawkish Fed rhetoric -> higher real rates / stronger dollar
   expected -> bearish for gold. direction="bearish", impact_level="medium" to "high"
   depending on how forceful and unexpected the comments are.
3. Headline: "Local football team wins championship" (news item). Not relevant to gold
   or macro markets at all. relevant=false, direction="neutral", impact_level="none",
   low confidence.

Be conservative with impact_level="high" — reserve it for events/news that would move
gold meaningfully in the hours after publication (major central-bank surprises, war/
crisis escalation, large inflation surprises). Most routine headlines are "low" or
"none". Write "summary" as a single short sentence a gold trader could scan in a feed
(no more than ~30 words). Respond only with the structured JSON — no extra commentary.
"""


class GoldNewsAnalyzer:
    def __init__(self, backend: AnalyzerBackend):
        self.backend = backend

    def analyze_news_item(self, item: NewsItem) -> Optional[AnalysisResult]:
        summary = (item.summary or "")[:_MAX_SUMMARY_CHARS]
        user_content = (
            f"Type: News article\n"
            f"Title: {item.title}\n"
            f"Source: {item.source}\n"
            f"Published: {item.published_at or 'unknown'}\n"
            f"Summary: {summary}"
        )
        return self._run(user_content)

    def analyze_calendar_event(self, event: CalendarEvent) -> Optional[AnalysisResult]:
        user_content = (
            f"Type: Economic calendar event\n"
            f"Title: {event.title}\n"
            f"Country: {event.country}\n"
            f"Scheduled: {event.event_date}\n"
            f"Source impact rating: {event.source_impact or 'unknown'}\n"
            f"Forecast: {event.forecast or 'n/a'}\n"
            f"Previous: {event.previous or 'n/a'}\n"
            f"Actual: {event.actual or 'not yet released'}"
        )
        return self._run(user_content)

    def _run(self, user_content: str) -> Optional[AnalysisResult]:
        raw_text = self.backend.generate(SYSTEM_PROMPT, user_content, ANALYSIS_SCHEMA)
        if raw_text is None:
            return None

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Failed to parse backend response as JSON: %s", exc)
            return None

        return AnalysisResult(
            relevant=data["relevant"],
            direction=data["direction"],
            impact_level=data["impact_level"],
            confidence=data["confidence"],
            summary=data["summary"],
            reasoning=data["reasoning"],
            model=self.backend.model,
            raw_response=raw_text,
        )

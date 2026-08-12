"""Orchestrates a single poll cycle: fetch -> dedupe -> prefilter -> analyze -> store -> output."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from src.analyzer import GoldNewsAnalyzer
from src.config import Config
from src.fetchers.calendar_fetcher import fetch_calendar_events
from src.fetchers.rss_fetcher import fetch_rss_items
from src.output import format_calendar_output, format_news_output
from src.prefilter import calendar_prefilter, matched_keywords
from src.storage import Storage

logger = logging.getLogger(__name__)


@dataclass
class PollStats:
    news_fetched: int = 0
    news_prefiltered_in: int = 0
    news_analyzed: int = 0
    calendar_fetched: int = 0
    calendar_analyzed: int = 0


class Pipeline:
    def __init__(self, config: Config, storage: Storage, analyzer: GoldNewsAnalyzer):
        self.config = config
        self.storage = storage
        self.analyzer = analyzer

    def run_once(self) -> PollStats:
        stats = PollStats()

        stats.news_fetched, stats.news_prefiltered_in, stats.news_analyzed = self._process_news()
        stats.calendar_fetched, stats.calendar_analyzed = self._process_calendar()

        logger.info(
            "Poll complete: news fetched=%d prefiltered_in=%d analyzed=%d | "
            "calendar fetched=%d analyzed=%d",
            stats.news_fetched,
            stats.news_prefiltered_in,
            stats.news_analyzed,
            stats.calendar_fetched,
            stats.calendar_analyzed,
        )
        return stats

    def run_forever(self) -> None:
        interval_seconds = self.config.poll_interval_minutes * 60
        logger.info("Starting poll loop (interval=%ds)", interval_seconds)
        try:
            while True:
                self.run_once()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Shutting down (interrupted)")

    def _process_news(self):
        items = fetch_rss_items(self.config.rss_feeds)
        prefiltered_in = 0
        analyzed = 0

        for item in items:
            if self.storage.news_item_exists(item.url):
                continue

            matches = matched_keywords(f"{item.title} {item.summary}")
            passed_prefilter = bool(matches)
            news_item_id = self.storage.save_news_item(
                item, passed_prefilter, ", ".join(sorted(matches))
            )

            if not passed_prefilter:
                continue

            prefiltered_in += 1
            result = self.analyzer.analyze_news_item(item)
            if result is None:
                self.storage.mark_news_item_status(news_item_id, "error")
                continue

            self.storage.save_news_analysis(news_item_id, result)
            analyzed += 1

            if result.relevant:
                print(format_news_output(item, result))
                print()

        return len(items), prefiltered_in, analyzed

    def _process_calendar(self):
        events = fetch_calendar_events(self.config.calendar_url)
        analyzed = 0

        for event in events:
            row_id, should_analyze = self.storage.upsert_calendar_event(event)

            if not should_analyze:
                continue
            if not calendar_prefilter(event.source_impact, event.title):
                continue

            result = self.analyzer.analyze_calendar_event(event)
            if result is None:
                continue

            trigger = event.status
            self.storage.save_calendar_analysis(row_id, trigger, result)
            analyzed += 1

            if result.relevant:
                print(format_calendar_output(event, trigger, result))
                print()

        return len(events), analyzed

"""Environment-driven configuration. Sensible defaults so .env isn't required to start."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

DEFAULT_RSS_FEEDS = [
    "https://www.kitco.com/rss/KitcoNews.xml",
    "https://www.fxstreet.com/rss/news",
    "https://www.investing.com/rss/news_11.rss",
    "https://www.forexlive.com/feed/news",
    "http://feeds.marketwatch.com/marketwatch/marketpulse/",
]

DEFAULT_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


@dataclass
class Config:
    analyzer_provider: str = "gemini"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-5"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    poll_interval_minutes: int = 5
    rss_feeds: List[str] = field(default_factory=lambda: list(DEFAULT_RSS_FEEDS))
    calendar_url: str = DEFAULT_CALENDAR_URL
    db_path: str = "data/gold_news.db"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()

        feeds_env = os.environ.get("RSS_FEEDS")
        rss_feeds = (
            [f.strip() for f in feeds_env.split(",") if f.strip()]
            if feeds_env
            else list(DEFAULT_RSS_FEEDS)
        )

        return cls(
            analyzer_provider=os.environ.get("ANALYZER_PROVIDER", "gemini").strip().lower(),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            claude_model=os.environ.get("CLAUDE_MODEL", "claude-sonnet-5"),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            poll_interval_minutes=int(os.environ.get("POLL_INTERVAL_MINUTES", "5")),
            rss_feeds=rss_feeds,
            calendar_url=os.environ.get("CALENDAR_URL", DEFAULT_CALENDAR_URL),
            db_path=os.environ.get("DB_PATH", "data/gold_news.db"),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
        )

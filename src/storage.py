"""SQLite persistence: dedupe, analysis records, and the future-distribution seam."""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from src.models import AnalysisResult, CalendarEvent, NewsItem

_SCHEMA = """
CREATE TABLE IF NOT EXISTS news_items (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    url                TEXT UNIQUE NOT NULL,
    content_hash       TEXT NOT NULL,
    title              TEXT NOT NULL,
    summary            TEXT,
    source             TEXT NOT NULL,
    published_at       TEXT,
    fetched_at         TEXT NOT NULL,
    prefilter_matched  INTEGER NOT NULL DEFAULT 0,
    matched_keywords   TEXT,
    analysis_status    TEXT NOT NULL DEFAULT 'pending'
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_news_items_url ON news_items(url);
CREATE INDEX IF NOT EXISTS idx_news_items_content_hash ON news_items(content_hash);

CREATE TABLE IF NOT EXISTS news_analysis (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    news_item_id   INTEGER NOT NULL REFERENCES news_items(id),
    relevant       INTEGER NOT NULL,
    direction      TEXT NOT NULL,
    impact_level   TEXT NOT NULL,
    confidence     REAL NOT NULL,
    summary        TEXT NOT NULL,
    reasoning      TEXT NOT NULL,
    model          TEXT NOT NULL,
    raw_response   TEXT NOT NULL,
    analyzed_at    TEXT NOT NULL,
    distributed_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_news_analysis_item ON news_analysis(news_item_id);

CREATE TABLE IF NOT EXISTS calendar_events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    event_key        TEXT UNIQUE NOT NULL,
    title            TEXT NOT NULL,
    country          TEXT NOT NULL,
    event_date       TEXT NOT NULL,
    source_impact    TEXT,
    forecast         TEXT,
    previous         TEXT,
    actual           TEXT,
    status           TEXT NOT NULL DEFAULT 'pending',
    first_seen_at    TEXT NOT NULL,
    last_updated_at  TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_calendar_events_key ON calendar_events(event_key);
CREATE INDEX IF NOT EXISTS idx_calendar_events_status ON calendar_events(status);

CREATE TABLE IF NOT EXISTS calendar_analysis (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    calendar_event_id  INTEGER NOT NULL REFERENCES calendar_events(id),
    analysis_trigger   TEXT NOT NULL,
    relevant           INTEGER NOT NULL,
    direction          TEXT NOT NULL,
    impact_level       TEXT NOT NULL,
    confidence         REAL NOT NULL,
    summary            TEXT NOT NULL,
    reasoning          TEXT NOT NULL,
    model              TEXT NOT NULL,
    raw_response       TEXT NOT NULL,
    analyzed_at        TEXT NOT NULL,
    distributed_at     TEXT
);
CREATE INDEX IF NOT EXISTS idx_calendar_analysis_event ON calendar_analysis(calendar_event_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Storage:
    def __init__(self, db_path: str):
        self.db_path = db_path
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self.init_db()

    def init_db(self) -> None:
        with self._conn:
            self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        self._conn.close()

    # -- News items ---------------------------------------------------------

    def news_item_exists(self, url: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM news_items WHERE url = ?", (url,)
        ).fetchone()
        return row is not None

    def save_news_item(
        self, item: NewsItem, prefilter_matched: bool, matched_keywords: str
    ) -> int:
        with self._conn:
            cursor = self._conn.execute(
                """
                INSERT INTO news_items
                    (url, content_hash, title, summary, source, published_at,
                     fetched_at, prefilter_matched, matched_keywords, analysis_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.url,
                    item.content_hash,
                    item.title,
                    item.summary,
                    item.source,
                    item.published_at,
                    _now(),
                    1 if prefilter_matched else 0,
                    matched_keywords,
                    "pending" if prefilter_matched else "filtered_out",
                ),
            )
            return cursor.lastrowid

    def mark_news_item_status(self, news_item_id: int, status: str) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE news_items SET analysis_status = ? WHERE id = ?",
                (status, news_item_id),
            )

    def save_news_analysis(self, news_item_id: int, result: AnalysisResult) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO news_analysis
                    (news_item_id, relevant, direction, impact_level, confidence,
                     summary, reasoning, model, raw_response, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    news_item_id,
                    1 if result.relevant else 0,
                    result.direction,
                    result.impact_level,
                    result.confidence,
                    result.summary,
                    result.reasoning,
                    result.model,
                    result.raw_response,
                    _now(),
                ),
            )
            self._conn.execute(
                "UPDATE news_items SET analysis_status = 'analyzed' WHERE id = ?",
                (news_item_id,),
            )

    # -- Calendar events ------------------------------------------------------

    def get_calendar_event_by_key(self, event_key: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM calendar_events WHERE event_key = ?", (event_key,)
        ).fetchone()

    def upsert_calendar_event(self, event: CalendarEvent) -> Tuple[int, bool]:
        """Insert or update a calendar event.

        Returns (row_id, should_analyze) where should_analyze is True on first
        sighting, or exactly once when the event transitions pending -> released.
        """
        existing = self.get_calendar_event_by_key(event.event_key)
        now = _now()

        if existing is None:
            with self._conn:
                cursor = self._conn.execute(
                    """
                    INSERT INTO calendar_events
                        (event_key, title, country, event_date, source_impact,
                         forecast, previous, actual, status, first_seen_at, last_updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_key,
                        event.title,
                        event.country,
                        event.event_date,
                        event.source_impact,
                        event.forecast,
                        event.previous,
                        event.actual,
                        event.status,
                        now,
                        now,
                    ),
                )
            return cursor.lastrowid, True

        was_pending = existing["status"] == "pending"
        just_released = was_pending and event.status == "released"

        with self._conn:
            self._conn.execute(
                """
                UPDATE calendar_events
                SET source_impact = ?, forecast = ?, previous = ?, actual = ?,
                    status = ?, last_updated_at = ?
                WHERE id = ?
                """,
                (
                    event.source_impact,
                    event.forecast,
                    event.previous,
                    event.actual,
                    event.status,
                    now,
                    existing["id"],
                ),
            )

        return existing["id"], just_released

    def save_calendar_analysis(
        self, calendar_event_id: int, trigger: str, result: AnalysisResult
    ) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO calendar_analysis
                    (calendar_event_id, analysis_trigger, relevant, direction,
                     impact_level, confidence, summary, reasoning, model,
                     raw_response, analyzed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    calendar_event_id,
                    trigger,
                    1 if result.relevant else 0,
                    result.direction,
                    result.impact_level,
                    result.confidence,
                    result.summary,
                    result.reasoning,
                    result.model,
                    result.raw_response,
                    _now(),
                ),
            )

    # -- Seam for a future distribution layer --------------------------------

    def get_unsent_analyses(self) -> List[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM news_analysis WHERE distributed_at IS NULL"
        ).fetchall()

    def mark_distributed(self, news_analysis_id: int) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE news_analysis SET distributed_at = ? WHERE id = ?",
                (_now(), news_analysis_id),
            )

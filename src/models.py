"""Dataclasses shared across fetchers, analyzer, and storage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class NewsItem:
    url: str
    title: str
    summary: str
    source: str
    published_at: Optional[str]
    content_hash: str


@dataclass
class CalendarEvent:
    event_key: str
    title: str
    country: str
    event_date: str
    source_impact: Optional[str]
    forecast: Optional[str]
    previous: Optional[str]
    actual: Optional[str]

    @property
    def status(self) -> str:
        return "released" if self.actual else "pending"


@dataclass
class AnalysisResult:
    relevant: bool
    direction: str
    impact_level: str
    confidence: float
    summary: str
    reasoning: str
    model: str
    raw_response: str

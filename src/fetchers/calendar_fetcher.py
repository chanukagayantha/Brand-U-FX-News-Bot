"""Fetch and parse the economic calendar feed into CalendarEvent records."""

from __future__ import annotations

import hashlib
import logging
from typing import List

import requests

from src.models import CalendarEvent

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; GoldNewsBot/1.0)"


def _event_key(country: str, title: str, event_date: str) -> str:
    normalized = f"{country.strip().lower()}|{title.strip().lower()}|{event_date.strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def fetch_calendar_events(calendar_url: str, timeout: int = 10) -> List[CalendarEvent]:
    """Fetch the weekly economic calendar. Returns [] on any failure — never aborts the cycle."""
    try:
        response = requests.get(
            calendar_url, timeout=timeout, headers={"User-Agent": _USER_AGENT}
        )
        response.raise_for_status()
        raw_events = response.json()
    except Exception as exc:  # noqa: BLE001 - a down calendar feed must not abort the cycle
        logger.warning("Failed to fetch economic calendar %s: %s", calendar_url, exc)
        return []

    events: List[CalendarEvent] = []
    for raw in raw_events:
        title = raw.get("title", "")
        country = raw.get("country", "")
        event_date = raw.get("date", "")

        if not title or not event_date:
            continue

        events.append(
            CalendarEvent(
                event_key=_event_key(country, title, event_date),
                title=title,
                country=country,
                event_date=event_date,
                source_impact=raw.get("impact"),
                forecast=raw.get("forecast") or None,
                previous=raw.get("previous") or None,
                actual=raw.get("actual") or None,
            )
        )

    return events

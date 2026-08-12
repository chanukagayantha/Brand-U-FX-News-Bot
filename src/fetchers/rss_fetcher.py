"""Fetch and parse gold/FX-relevant RSS feeds into NewsItem records."""

from __future__ import annotations

import hashlib
import logging
import re
from typing import List
from urllib.parse import urlsplit, urlunsplit

import feedparser
import requests

from src.models import NewsItem

logger = logging.getLogger(__name__)

_USER_AGENT = "Mozilla/5.0 (compatible; GoldNewsBot/1.0)"
_TRACKING_PARAM_RE = re.compile(r"^(utm_|fbclid|gclid)", re.IGNORECASE)


def _normalize_url(url: str) -> str:
    """Strip tracking query params so the same article doesn't dedupe as new."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    kept = [
        pair
        for pair in parts.query.split("&")
        if pair and not _TRACKING_PARAM_RE.match(pair.split("=", 1)[0])
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(kept), ""))


def _content_hash(title: str, summary: str) -> str:
    normalized = f"{title.strip().lower()}|{summary.strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def fetch_rss_items(feed_urls: List[str], timeout: int = 10) -> List[NewsItem]:
    """Fetch every feed independently — one broken feed never aborts the cycle."""
    items: List[NewsItem] = []
    for feed_url in feed_urls:
        try:
            response = requests.get(
                feed_url, timeout=timeout, headers={"User-Agent": _USER_AGENT}
            )
            response.raise_for_status()
            parsed = feedparser.parse(response.content)
        except Exception as exc:  # noqa: BLE001 - one bad feed must not abort the cycle
            logger.warning("Failed to fetch RSS feed %s: %s", feed_url, exc)
            continue

        source = parsed.feed.get("title", feed_url) if hasattr(parsed, "feed") else feed_url

        for entry in parsed.entries:
            url = entry.get("link", "")
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            published_at = entry.get("published", entry.get("updated"))

            if not url or not title:
                continue

            items.append(
                NewsItem(
                    url=_normalize_url(url),
                    title=title,
                    summary=summary,
                    source=source,
                    published_at=published_at,
                    content_hash=_content_hash(title, summary),
                )
            )

    return items

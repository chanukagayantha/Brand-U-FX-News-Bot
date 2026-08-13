"""Cheap keyword-based relevance filter, applied before any LLM call."""

from __future__ import annotations

import re
from typing import Set

# Multi-word/unambiguous terms: plain substring match is fine.
_PHRASE_KEYWORDS = {
    "gold",
    "xau",
    "bullion",
    "safe haven",
    "safe-haven",
    "central bank",
    "interest rate",
    "rate hike",
    "rate cut",
    "rate decision",
    "treasury yield",
    "treasury yields",
    "quantitative easing",
    "quantitative tightening",
    "geopolitical",
    "recession",
    "inflation",
    "tariff",
    "tariffs",
    "sanctions",
    "powell",
    "federal reserve",
    "fomc",
    "dollar index",
}

# Short/ambiguous tokens: require word boundaries so "cpi" doesn't match "principal", etc.
_WORD_KEYWORDS = {
    "fed",
    "cpi",
    "pce",
    "ppi",
    "nfp",
    "gdp",
    "dxy",
}

_WORD_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in _WORD_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def matched_keywords(text: str) -> Set[str]:
    lowered = text.lower()
    matches = {kw for kw in _PHRASE_KEYWORDS if kw in lowered}
    matches.update(m.lower() for m in _WORD_PATTERN.findall(text))
    return matches


def is_relevant(text: str) -> bool:
    return bool(matched_keywords(text))


def calendar_prefilter(source_impact: str | None, title: str) -> bool:
    """Calendar events are gated on impact level first, then the same keyword check."""
    if not source_impact or source_impact.strip().lower() not in ("high", "medium"):
        return False
    return is_relevant(title)

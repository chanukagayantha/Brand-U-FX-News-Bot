"""Provider-agnostic backend interface for LLM impact analysis."""

from __future__ import annotations

import abc
from typing import Optional


class AnalyzerBackend(abc.ABC):
    """One LLM provider's request/response handling for a single analysis call.

    Implementations own everything provider-specific: request construction,
    structured-output configuration, and mapping provider errors (rate limits,
    connection failures, safety refusals, truncation) to a `None` return.
    `generate()` must never raise — every failure path is logged and returns None.
    """

    model: str

    @abc.abstractmethod
    def generate(self, system_prompt: str, user_content: str, schema: dict) -> Optional[str]:
        """Send one request. Return the raw JSON response text, or None on any failure."""
        raise NotImplementedError

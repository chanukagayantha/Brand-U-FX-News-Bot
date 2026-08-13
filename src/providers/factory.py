"""Selects the configured LLM backend. The only place both SDKs are imported together."""

from __future__ import annotations

import anthropic
from google import genai

from src.config import Config
from src.providers.base import AnalyzerBackend
from src.providers.claude_backend import ClaudeBackend
from src.providers.gemini_backend import GeminiBackend


def create_backend(config: Config) -> AnalyzerBackend:
    provider = config.analyzer_provider

    if provider == "claude":
        client = anthropic.Anthropic(api_key=config.anthropic_api_key)
        return ClaudeBackend(client=client, model=config.claude_model)

    if provider == "gemini":
        client = genai.Client(api_key=config.gemini_api_key)
        return GeminiBackend(client=client, model=config.gemini_model)

    raise ValueError(f"Unknown ANALYZER_PROVIDER: {provider!r} (expected 'claude' or 'gemini')")

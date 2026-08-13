"""Claude (Anthropic) backend for gold market impact analysis."""

from __future__ import annotations

import logging
from typing import Optional

import anthropic

from src.providers.base import AnalyzerBackend

logger = logging.getLogger(__name__)


class ClaudeBackend(AnalyzerBackend):
    def __init__(self, client: Optional[anthropic.Anthropic] = None, model: str = "claude-sonnet-5"):
        self.client = client or anthropic.Anthropic()
        self.model = model

    def generate(self, system_prompt: str, user_content: str, schema: dict) -> Optional[str]:
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=700,
                thinking={"type": "disabled"},
                output_config={
                    "effort": "low",
                    "format": {"type": "json_schema", "schema": schema},
                },
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_content}],
            )
        except anthropic.RateLimitError as exc:
            logger.warning("Rate limited by Claude API: %s", exc)
            return None
        except anthropic.APIConnectionError as exc:
            logger.warning("Connection error calling Claude API: %s", exc)
            return None
        except anthropic.APIStatusError as exc:
            logger.warning("Claude API error (%s): %s", exc.status_code, exc.message)
            return None

        if response.stop_reason == "refusal":
            logger.warning("Claude refused to analyze this item")
            return None
        if response.stop_reason == "max_tokens":
            logger.warning("Claude response truncated at max_tokens")
            return None

        text_block = next((b for b in response.content if b.type == "text"), None)
        if text_block is None:
            logger.warning("Claude response had no text block")
            return None

        return text_block.text

"""Gemini (Google) backend for gold market impact analysis."""

from __future__ import annotations

import logging
from typing import Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from src.providers.base import AnalyzerBackend

logger = logging.getLogger(__name__)

# FinishReason is a str-subclass enum; comparing/containment against plain
# string literals works directly (verified: `FinishReason.SAFETY == "SAFETY"`).
_BLOCKED_FINISH_REASONS = {"SAFETY", "PROHIBITED_CONTENT", "RECITATION", "BLOCKLIST", "SPII", "OTHER"}


class GeminiBackend(AnalyzerBackend):
    def __init__(self, client: Optional[genai.Client] = None, model: str = "gemini-2.5-flash"):
        self.client = client or genai.Client()
        self.model = model

    def generate(self, system_prompt: str, user_content: str, schema: dict) -> Optional[str]:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    # response_json_schema (not response_schema) accepts standard
                    # JSON Schema, including additionalProperties, with no translation.
                    response_json_schema=schema,
                    max_output_tokens=700,
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                ),
            )
        except genai_errors.ClientError as exc:
            if exc.code == 429:
                logger.warning("Rate limited by Gemini API: %s", exc)
            else:
                logger.warning("Gemini API client error (%s): %s", exc.code, exc.message)
            return None
        except genai_errors.ServerError as exc:
            logger.warning("Gemini API server error (%s): %s", exc.code, exc.message)
            return None
        except genai_errors.APIError as exc:
            logger.warning("Gemini API error: %s", exc)
            return None
        except Exception as exc:  # noqa: BLE001 - transport failures aren't wrapped by the SDK
            logger.warning("Unexpected error calling Gemini API: %s", exc)
            return None

        candidates = response.candidates
        if candidates:
            finish_reason = candidates[0].finish_reason
            if finish_reason in _BLOCKED_FINISH_REASONS:
                logger.warning("Gemini refused/blocked this item (finish_reason=%s)", finish_reason)
                return None
            if finish_reason == "MAX_TOKENS":
                logger.warning("Gemini response truncated at max_output_tokens")
                return None

        text = response.text
        if not text:
            logger.warning("Gemini response had no text content")
            return None
        return text

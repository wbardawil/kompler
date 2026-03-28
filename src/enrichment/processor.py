"""Claude API processor for document enrichment.

Implements the LLMProvider interface using Anthropic's Claude API.
Uses Haiku for fast/cheap classification, Sonnet for deep extraction and Q&A.
"""

import json
import logging
from typing import Any

import anthropic

from src.core.config import get_settings
from src.core.interfaces import LLMProvider
from src.enrichment.prompts import (
    CLASSIFY_PROMPT,
    EXTRACT_ENTITIES_PROMPT,
    PROMPT_VERSION,
    QA_PROMPT,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class ClaudeProvider(LLMProvider):
    """Claude API implementation of LLMProvider."""

    def __init__(self) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def classify(self, text: str, prompt: str | None = None) -> dict[str, Any]:
        """Classify a document using Haiku (fast, cheap — 0.5 credits)."""
        truncated = text[:8000]  # Haiku context limit optimization

        response = await self._client.messages.create(
            model=settings.claude_classify_model,
            max_tokens=1024,
            system=prompt or CLASSIFY_PROMPT,
            messages=[{"role": "user", "content": truncated}],
        )

        result = _parse_json_response(response.content[0].text)
        result["prompt_version"] = PROMPT_VERSION
        result["model"] = settings.claude_classify_model
        result["input_tokens"] = response.usage.input_tokens
        result["output_tokens"] = response.usage.output_tokens
        return result

    async def extract_entities(self, text: str, prompt: str | None = None) -> list[dict[str, Any]]:
        """Extract entities using Sonnet (accurate — 2.0 credits)."""
        truncated = text[:30000]  # Sonnet can handle more context

        response = await self._client.messages.create(
            model=settings.claude_extract_model,
            max_tokens=4096,
            system=prompt or EXTRACT_ENTITIES_PROMPT,
            messages=[{"role": "user", "content": truncated}],
        )

        result = _parse_json_response(response.content[0].text)
        # Ensure we always return the expected structure
        if isinstance(result, list):
            result = {"entities": result, "relationships": []}
        if "entities" not in result:
            result["entities"] = []
        if "relationships" not in result:
            result["relationships"] = []

        result["prompt_version"] = PROMPT_VERSION
        result["model"] = settings.claude_extract_model
        result["input_tokens"] = response.usage.input_tokens
        result["output_tokens"] = response.usage.output_tokens
        return result

    async def generate_answer(
        self, question: str, context_chunks: list[str], prompt: str | None = None
    ) -> dict[str, Any]:
        """Answer a question using RAG context. Uses Sonnet (0 credits — Q&A is free)."""
        context = "\n\n---\n\n".join(context_chunks)
        system = (prompt or QA_PROMPT).replace("{context}", context)

        response = await self._client.messages.create(
            model=settings.claude_qa_model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": question}],
        )

        result = _parse_json_response(response.content[0].text)
        result["model"] = settings.claude_qa_model
        result["input_tokens"] = response.usage.input_tokens
        result["output_tokens"] = response.usage.output_tokens
        return result


def _parse_json_response(text: str) -> dict[str, Any]:
    """Parse JSON from Claude's response, handling markdown code blocks."""
    cleaned = text.strip()

    # Strip markdown code blocks if present
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse Claude response as JSON: %s", cleaned[:200])
        return {"raw_response": text, "parse_error": True}

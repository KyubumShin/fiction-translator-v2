"""Persona learner node -- extracts character insights from translations.

Analyses translated text to discover or refine character personas,
producing suggestions that can be reviewed and applied to the persona DB.
"""
from __future__ import annotations

import logging
from typing import Any

from fiction_translator.pipeline.state import TranslationState
from fiction_translator.pipeline.callbacks import notify

logger = logging.getLogger(__name__)


async def persona_learner_node(state: TranslationState) -> dict:
    """Extract character insights from translations for persona updates.

    Returns persona_suggestions -- a list of dicts describing suggested
    updates to persona records.
    """
    translated_segments = state.get("translated_segments", [])
    detected_characters = state.get("detected_characters", [])
    existing_personas = state.get("existing_personas", [])
    callback = state.get("progress_callback")

    await notify(callback, "persona_learning", 0.0, "Analysing character voices...")

    if not translated_segments or not detected_characters:
        return {"persona_suggestions": []}

    api_keys = state.get("api_keys", {})
    if not api_keys:
        return {"persona_suggestions": []}

    try:
        from fiction_translator.llm.providers import get_llm_provider
        from fiction_translator.llm.prompts.persona_analysis import (
            build_persona_analysis_prompt,
        )

        provider = get_llm_provider(
            state.get("llm_provider", "gemini"),
            api_keys=api_keys,
        )

        # Build translated text for analysis
        sorted_segs = sorted(
            translated_segments,
            key=lambda s: s.get("segment_id", s.get("order", 0)),
        )
        translated_text = "\n".join(
            s.get("translated_text", "") for s in sorted_segs
            if s.get("translated_text")
        )

        if not translated_text.strip():
            return {"persona_suggestions": []}

        prompt = build_persona_analysis_prompt(
            translated_text=translated_text,
            detected_characters=detected_characters,
            existing_personas=existing_personas,
            target_language=state.get("target_language", "en"),
        )

        result = await provider.generate_json(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        raw_updates = result.get("persona_updates", [])

        # Normalise and filter suggestions
        suggestions: list[dict] = []
        valid_fields = {"personality", "speech_style", "formality_level", "aliases"}

        for update in raw_updates:
            name = update.get("name", "").strip()
            field = update.get("field", "").strip()
            value = update.get("value")
            confidence = update.get("confidence", 0.5)

            if not name or not field or not value:
                continue
            if field not in valid_fields:
                continue
            if confidence < 0.3:
                continue

            # Match to existing persona if possible
            persona_id = _find_persona_id(name, existing_personas)

            suggestions.append({
                "name": name,
                "persona_id": persona_id,
                "field": field,
                "value": str(value),
                "confidence": confidence,
                "evidence": update.get("evidence", ""),
            })

        await notify(
            callback, "persona_learning", 1.0,
            f"Found {len(suggestions)} persona suggestions",
        )

        return {"persona_suggestions": suggestions}

    except Exception as e:
        logger.error("Persona learning failed: %s", e)
        return {"persona_suggestions": []}


def _find_persona_id(
    name: str,
    existing_personas: list[dict],
) -> int | None:
    """Find the persona ID matching a character name."""
    name_lower = name.lower()
    for p in existing_personas:
        if p.get("name", "").lower() == name_lower:
            return p.get("id")
        for alias in (p.get("aliases") or []):
            if alias.lower() == name_lower:
                return p.get("id")
    return None

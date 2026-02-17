"""Relationship learner node -- detects character relationships from translations.

Analyses translated text to discover or update character relationships,
producing suggestions that can be applied to the relationship DB.
"""
from __future__ import annotations

import logging

from fiction_translator.pipeline.callbacks import notify
from fiction_translator.pipeline.state import TranslationState

logger = logging.getLogger(__name__)


async def relationship_learner_node(state: TranslationState) -> dict:
    """Detect character relationships from translated text.

    Returns relationship_suggestions -- a list of dicts describing
    detected or updated relationships.
    """
    translated_segments = state.get("translated_segments", [])
    detected_characters = state.get("detected_characters", [])
    existing_personas = state.get("existing_personas", [])
    existing_relationships = state.get("existing_relationships", [])
    callback = state.get("progress_callback")

    await notify(callback, "relationship_learning", 0.0, "Analysing character relationships...")

    if not translated_segments or not detected_characters:
        return {"relationship_suggestions": []}

    api_keys = state.get("api_keys", {})
    if not api_keys:
        return {"relationship_suggestions": []}

    try:
        from fiction_translator.llm.prompts.relationship_analysis import (
            build_relationship_analysis_prompt,
        )
        from fiction_translator.llm.providers import get_llm_provider

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
            return {"relationship_suggestions": []}

        prompt = build_relationship_analysis_prompt(
            translated_text=translated_text,
            detected_characters=detected_characters,
            existing_personas=existing_personas,
            existing_relationships=existing_relationships,
            target_language=state.get("target_language", "en"),
            source_language=state.get("source_language", "ko"),
        )

        result = await provider.generate_json(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4096,
        )

        raw_updates = result.get("relationship_updates", [])

        valid_types = {
            "friend", "rival", "family", "romantic", "mentor",
            "subordinate", "enemy", "ally", "acquaintance",
        }
        suggestions: list[dict] = []

        for update in raw_updates:
            char_1 = update.get("character_1", "").strip()
            char_2 = update.get("character_2", "").strip()
            rel_type = update.get("relationship_type", "").strip()
            intimacy = update.get("intimacy_level", 5)
            confidence = update.get("confidence", 0.5)

            if not char_1 or not char_2 or not rel_type:
                continue
            if rel_type not in valid_types:
                continue
            if confidence < 0.3:
                continue

            # Clamp intimacy
            intimacy = max(1, min(10, int(intimacy)))

            persona_id_1 = _find_persona_id(char_1, existing_personas)
            persona_id_2 = _find_persona_id(char_2, existing_personas)

            suggestions.append({
                "character_1": char_1,
                "character_2": char_2,
                "persona_id_1": persona_id_1,
                "persona_id_2": persona_id_2,
                "relationship_type": rel_type,
                "intimacy_level": intimacy,
                "description": update.get("description", ""),
                "confidence": confidence,
                "evidence": update.get("evidence", ""),
            })

        await notify(
            callback, "relationship_learning", 1.0,
            f"Found {len(suggestions)} relationship suggestions",
        )

        return {"relationship_suggestions": suggestions}

    except Exception as e:
        logger.error("Relationship learning failed: %s", e)
        return {"relationship_suggestions": []}


def _find_persona_id(name: str, existing_personas: list[dict]) -> int | None:
    """Find the persona ID matching a character name."""
    name_lower = name.lower()
    for p in existing_personas:
        if p.get("name", "").lower() == name_lower:
            return p.get("id")
        for alias in (p.get("aliases") or []):
            if alias.lower() == name_lower:
                return p.get("id")
    return None

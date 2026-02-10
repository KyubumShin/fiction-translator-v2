"""Character extractor node -- identifies characters from text segments.

Uses a hybrid approach: regex-based speaker extraction from dialogue
segments, optionally enhanced with LLM analysis for deeper character
identification.
"""
from __future__ import annotations

import re
import logging
from collections import Counter
from typing import Any

from fiction_translator.pipeline.state import TranslationState
from fiction_translator.pipeline.callbacks import notify

logger = logging.getLogger(__name__)

# Speaker detection patterns per language (same as segmenter, but used
# here to aggregate characters across all segments).
SPEAKER_PATTERNS: dict[str, list[re.Pattern]] = {
    "ko": [
        re.compile(r'["\u201D]\s*(?:\ub77c\uace0|\uc774\ub77c\uace0)\s+(\w+)'),
        re.compile(r'(\w+)[\uc774\uac00\uc740\ub294]\s+\ub9d0\ud588\ub2e4'),
        re.compile(r'(\w+)\s*:\s*["\u201C]'),
    ],
    "ja": [
        re.compile(r'\u300D\u3068(\w+)'),
        re.compile(r'(\w+)\u306F\u8A00\u3063\u305F'),
    ],
    "zh": [
        re.compile(r'\u201D(\w+)\u8BF4'),
        re.compile(r'(\w+)\u8BF4\s*[:\uFF1A]\s*\u201C'),
    ],
    "en": [
        re.compile(r'["\u201D]\s+said\s+(\w+)', re.IGNORECASE),
        re.compile(r'(\w+)\s+said[,.]?\s*["\u201C]', re.IGNORECASE),
        re.compile(r'(\w+)\s*:\s*["\u201C]'),
    ],
}


async def character_extractor_node(state: TranslationState) -> dict:
    """Extract characters using regex patterns + optional LLM analysis."""
    segments = state.get("segments", [])
    source_language = state.get("source_language", "ko")
    existing_personas = state.get("existing_personas", [])
    callback = state.get("progress_callback")

    await notify(callback, "character_extraction", 0.0, "Extracting characters...")

    # ── 1. Pattern-based extraction from segments ────────────────────
    speaker_counts: Counter = Counter()
    patterns = SPEAKER_PATTERNS.get(source_language, SPEAKER_PATTERNS["en"])

    for seg in segments:
        # Use speaker from segmentation if available
        if seg.get("speaker"):
            speaker_counts[seg["speaker"]] += 1
            continue

        # Only scan dialogue segments
        if seg.get("type") != "dialogue":
            continue

        text = seg.get("text", "")
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                name = match.group(1).strip()
                if len(name) >= 1:
                    speaker_counts[name] += 1
                break

    # Build initial character list from regex
    detected: list[dict] = []
    for name, count in speaker_counts.most_common():
        detected.append({
            "name": name,
            "aliases": [],
            "role": "supporting",
            "speaking_lines": count,
            "personality_hints": None,
            "speech_style_hints": None,
            "source": "regex",
        })

    # ── 2. LLM-based extraction for deeper analysis ──────────────────
    api_keys = state.get("api_keys", {})
    if api_keys and segments:
        try:
            from fiction_translator.llm.providers import get_llm_provider
            from fiction_translator.llm.prompts.character_extraction import (
                build_character_extraction_prompt,
            )

            provider = get_llm_provider(
                state.get("llm_provider", "gemini"),
                api_keys=api_keys,
            )

            # Concatenate segment texts (cap at ~8000 chars for token efficiency)
            all_text = "\n".join(s.get("text", "") for s in segments)
            if len(all_text) > 8000:
                all_text = all_text[:8000]

            prompt = build_character_extraction_prompt(
                all_text, source_language, existing_personas,
            )
            result = await provider.generate_json(
                prompt=prompt, temperature=0.2, max_tokens=2048,
            )
            llm_chars = result.get("characters", [])
            if llm_chars:
                detected = _merge_characters(detected, llm_chars)
        except Exception as e:
            logger.warning("LLM character extraction failed: %s", e)

    # ── 3. Merge with existing personas from DB ──────────────────────
    detected = _merge_with_existing(detected, existing_personas)

    await notify(
        callback, "character_extraction", 1.0,
        f"Detected {len(detected)} characters",
    )

    return {"detected_characters": detected}


def _merge_characters(
    regex_chars: list[dict],
    llm_chars: list[dict],
) -> list[dict]:
    """Merge regex-detected characters with LLM-detected characters.

    LLM results are richer, so they take precedence.  Regex results
    add any characters the LLM missed.
    """
    by_name: dict[str, dict] = {}

    # LLM results first (higher quality)
    for ch in llm_chars:
        name = ch.get("name", "").strip()
        if not name:
            continue
        ch["source"] = "llm"
        by_name[name.lower()] = ch

    # Add regex-only characters
    for ch in regex_chars:
        name = ch.get("name", "").strip()
        if not name:
            continue
        key = name.lower()
        if key not in by_name:
            by_name[key] = ch
        else:
            # Merge speaking line count
            existing = by_name[key]
            existing["speaking_lines"] = max(
                existing.get("speaking_lines", 0),
                ch.get("speaking_lines", 0),
            )

    return list(by_name.values())


def _merge_with_existing(
    detected: list[dict],
    existing_personas: list[dict],
) -> list[dict]:
    """Cross-reference detected characters with known personas.

    Updates detected entries to use canonical names from the DB when
    a match is found (exact or alias match).
    """
    if not existing_personas:
        return detected

    # Build lookup: lowercase name/alias -> persona dict
    persona_lookup: dict[str, dict] = {}
    for p in existing_personas:
        persona_lookup[p["name"].lower()] = p
        for alias in (p.get("aliases") or []):
            persona_lookup[alias.lower()] = p

    for ch in detected:
        name_lower = ch["name"].lower()
        matched_persona = persona_lookup.get(name_lower)

        # Also check aliases from detected character
        if not matched_persona:
            for alias in (ch.get("aliases") or []):
                matched_persona = persona_lookup.get(alias.lower())
                if matched_persona:
                    break

        if matched_persona:
            ch["persona_id"] = matched_persona.get("id")
            ch["canonical_name"] = matched_persona["name"]

    return detected

"""Segmenter node -- splits source text into translatable segments.

Uses a hybrid approach: deterministic rule-based splitting first, with
optional LLM refinement for short texts.  Computes character offsets for
every segment so the editor can do click-to-highlight.
"""
from __future__ import annotations

import re
import logging
from typing import Any

from fiction_translator.pipeline.state import TranslationState, SegmentData
from fiction_translator.pipeline.callbacks import notify

logger = logging.getLogger(__name__)

# ── Language-specific dialogue markers ────────────────────────────────
DIALOGUE_MARKERS: dict[str, list[re.Pattern]] = {
    "ko": [
        re.compile(r'^["\u201C].*["\u201D]\s*$'),        # "..." full line
        re.compile(r'^["\u201C]'),                        # starts with "
        re.compile(r'^\u300C.*\u300D'),                   # Korean angular quotes
    ],
    "ja": [
        re.compile(r'^\u300C.*\u300D'),                   # Japanese brackets
        re.compile(r'^\u300E.*\u300F'),                   # double brackets
        re.compile(r'^["\u201C].*["\u201D]'),
    ],
    "zh": [
        re.compile(r'^\u201C.*\u201D'),                   # Chinese quotes
        re.compile(r'^["\u300C]'),
    ],
    "en": [
        re.compile(r'^["\u201C].*["\u201D]\s*$'),
        re.compile(r'^["\u201C]'),
        re.compile(r"^'.*'\s*$"),
    ],
}

# Speaker attribution patterns per language
SPEAKER_PATTERNS: dict[str, list[re.Pattern]] = {
    "ko": [
        re.compile(r'["\u201D]\s*(?:\ub77c\uace0|\uc774\ub77c\uace0)\s+(\w+)'),
        re.compile(r'(\w+)[\\uc774\uac00\uc740\ub294]\s+\ub9d0\ud588\ub2e4'),
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


# ── Public node function ─────────────────────────────────────────────

async def segmenter_node(state: TranslationState) -> dict:
    """Segment source text into translatable units with offset tracking."""
    source_text = state["source_text"]
    source_language = state.get("source_language", "ko")
    callback = state.get("progress_callback")

    await notify(callback, "segmentation", 0.0, "Segmenting text...")

    # Primary: rule-based segmentation (always runs)
    segments = _rule_based_segment(source_text, source_language)

    # Optional: LLM refinement for short texts
    api_keys = state.get("api_keys", {})
    if api_keys and len(source_text) < 10000:
        try:
            from fiction_translator.llm.providers import get_llm_provider
            from fiction_translator.llm.prompts.segmentation import (
                build_segmentation_prompt,
            )

            provider = get_llm_provider(
                state.get("llm_provider", "gemini"),
                api_keys=api_keys,
            )
            prompt = build_segmentation_prompt(source_text, source_language)
            result = await provider.generate_json(
                prompt=prompt, temperature=0.1, max_tokens=4096,
            )
            llm_segments = result.get("segments", [])
            if llm_segments:
                parsed = _parse_llm_segments(llm_segments, source_text)
                if parsed:
                    segments = parsed
        except Exception as e:
            logger.warning("LLM segmentation failed, using rule-based: %s", e)

    await notify(
        callback, "segmentation", 1.0,
        f"Segmented into {len(segments)} segments",
    )

    return {"segments": segments}


# ── Rule-based segmentation ──────────────────────────────────────────

def _rule_based_segment(
    source_text: str,
    source_language: str,
) -> list[SegmentData]:
    """Split text into segments using paragraph boundaries and dialogue markers.

    Returns a list of SegmentData dicts with correct character offsets into
    the original *source_text*.
    """
    if not source_text.strip():
        return []

    paragraphs = _split_paragraphs(source_text)
    dialogue_patterns = DIALOGUE_MARKERS.get(source_language, DIALOGUE_MARKERS["en"])
    speaker_patterns = SPEAKER_PATTERNS.get(source_language, SPEAKER_PATTERNS["en"])

    segments: list[SegmentData] = []
    order = 0

    for para_text, para_start in paragraphs:
        stripped = para_text.strip()
        if not stripped:
            continue

        seg_type = _classify_segment(stripped, dialogue_patterns)
        speaker = _detect_speaker(stripped, speaker_patterns) if seg_type == "dialogue" else None

        segments.append(SegmentData(
            id=None,
            order=order,
            text=stripped,
            type=seg_type,
            speaker=speaker,
            source_start_offset=para_start + (len(para_text) - len(para_text.lstrip())),
            source_end_offset=para_start + len(para_text.rstrip()),
        ))
        order += 1

    return segments


def _split_paragraphs(text: str) -> list[tuple[str, int]]:
    """Split text on double-newline boundaries, tracking start offsets.

    Returns list of (paragraph_text, start_offset) tuples.  Single-newline
    boundaries inside a paragraph are preserved.
    """
    results: list[tuple[str, int]] = []
    # Split on one or more blank lines (two+ consecutive newlines)
    parts = re.split(r'(\n\s*\n)', text)

    offset = 0
    for part in parts:
        stripped = part.strip()
        if stripped:
            # Find the actual start within the part (skip leading whitespace)
            leading = len(part) - len(part.lstrip())
            results.append((stripped, offset + leading))
        offset += len(part)

    return results


def _classify_segment(
    text: str,
    dialogue_patterns: list[re.Pattern],
) -> str:
    """Classify a segment as narrative, dialogue, action, or thought."""
    for pattern in dialogue_patterns:
        if pattern.search(text):
            return "dialogue"

    # Heuristic for thought (internal monologue markers)
    thought_markers = [
        re.compile(r"^\u2018.*\u2019$"),           # 'thought'
        re.compile(r"^\(.*\)$"),                    # (thought)
        re.compile(r"^[\u3008\u3010].*[\u3009\u3011]$"),  # CJK brackets
    ]
    for pattern in thought_markers:
        if pattern.search(text):
            return "thought"

    return "narrative"


def _detect_speaker(
    text: str,
    speaker_patterns: list[re.Pattern],
) -> str | None:
    """Try to extract a speaker name from dialogue text."""
    for pattern in speaker_patterns:
        match = pattern.search(text)
        if match:
            return match.group(1).strip()
    return None


# ── LLM segment parsing ─────────────────────────────────────────────

def _parse_llm_segments(
    llm_segments: list[dict],
    source_text: str,
) -> list[SegmentData]:
    """Convert LLM JSON output to SegmentData list with computed offsets.

    The LLM returns segments with 'text', 'type', 'speaker' keys.
    We locate each segment's text within *source_text* to compute offsets.
    """
    results: list[SegmentData] = []
    search_start = 0
    order = 0

    for seg in llm_segments:
        seg_text = seg.get("text", "").strip()
        if not seg_text:
            continue

        # Find this segment's text in the source
        idx = source_text.find(seg_text, search_start)
        if idx == -1:
            # Fuzzy fallback: try first 50 chars
            short = seg_text[:50]
            idx = source_text.find(short, search_start)
            if idx == -1:
                # Cannot locate -- use approximate offset
                idx = search_start

        start_offset = idx
        end_offset = idx + len(seg_text)
        search_start = end_offset

        seg_type = seg.get("type", "narrative")
        if seg_type not in ("narrative", "dialogue", "action", "thought"):
            seg_type = "narrative"

        results.append(SegmentData(
            id=None,
            order=order,
            text=seg_text,
            type=seg_type,
            speaker=seg.get("speaker"),
            source_start_offset=start_offset,
            source_end_offset=end_offset,
        ))
        order += 1

    return results

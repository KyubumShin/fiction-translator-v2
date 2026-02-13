"""Validator node -- checks segmentation quality before translation.

Runs deterministic checks on segments to catch common issues.
If validation fails, the pipeline can loop back to re-segment.
"""
from __future__ import annotations

import logging

from fiction_translator.pipeline.callbacks import notify
from fiction_translator.pipeline.state import TranslationState

logger = logging.getLogger(__name__)

# Maximum allowed segment length in characters
MAX_SEGMENT_LENGTH = 10000
# Minimum coverage ratio (segment text vs source text)
MIN_COVERAGE_RATIO = 0.80


async def validator_node(state: TranslationState) -> dict:
    """Validate segmentation quality.

    Returns validation_passed, validation_errors, and incremented
    validation_attempts.
    """
    segments = state.get("segments", [])
    source_text = state.get("source_text", "")
    callback = state.get("progress_callback")
    attempts = state.get("validation_attempts", 0) + 1

    await notify(callback, "validation", 0.0, f"Validating segments (attempt {attempts})...")

    validation_errors: list[str] = []

    # ── Check 1: Must have at least one segment ──────────────────────
    if not segments:
        validation_errors.append("No segments produced")
        return {
            "validation_passed": False,
            "validation_errors": validation_errors,
            "validation_attempts": attempts,
        }

    # ── Check 2: No empty segments ───────────────────────────────────
    for i, seg in enumerate(segments):
        text = seg.get("text", "").strip()
        if not text:
            validation_errors.append(f"Segment {i} is empty")

    # ── Check 3: No oversized segments ───────────────────────────────
    for i, seg in enumerate(segments):
        text = seg.get("text", "")
        if len(text) > MAX_SEGMENT_LENGTH:
            validation_errors.append(
                f"Segment {i} exceeds max length ({len(text)} > {MAX_SEGMENT_LENGTH})"
            )

    # ── Check 4: Offsets are non-negative and ordered ────────────────
    prev_end = -1
    for i, seg in enumerate(segments):
        start = seg.get("source_start_offset", 0)
        end = seg.get("source_end_offset", 0)

        if start < 0 or end < 0:
            validation_errors.append(f"Segment {i} has negative offset")
        if end < start:
            validation_errors.append(
                f"Segment {i} end offset ({end}) < start offset ({start})"
            )
        if start < prev_end:
            # Overlapping segments -- warning only, not fatal
            logger.warning("Segment %d overlaps with previous (start=%d, prev_end=%d)", i, start, prev_end)
        prev_end = end

    # ── Check 5: Coverage -- segments should cover most of source ────
    if source_text and segments:
        total_seg_chars = sum(len(s.get("text", "")) for s in segments)
        source_chars = len(source_text.strip())
        if source_chars > 0:
            coverage = total_seg_chars / source_chars
            if coverage < MIN_COVERAGE_RATIO:
                validation_errors.append(
                    f"Low coverage: segments cover {coverage:.0%} of source text "
                    f"(minimum {MIN_COVERAGE_RATIO:.0%})"
                )

    # ── Check 6: Segment types are valid ─────────────────────────────
    valid_types = {"narrative", "dialogue", "action", "thought"}
    for i, seg in enumerate(segments):
        seg_type = seg.get("type", "")
        if seg_type not in valid_types:
            validation_errors.append(
                f"Segment {i} has invalid type '{seg_type}'"
            )

    # ── Check 7: Dialogue segments should ideally have speakers ──────
    dialogue_count = sum(1 for s in segments if s.get("type") == "dialogue")
    speaker_count = sum(
        1 for s in segments
        if s.get("type") == "dialogue" and s.get("speaker")
    )
    if dialogue_count > 0 and speaker_count == 0:
        # Warn but do not fail -- speaker detection is best-effort
        logger.warning(
            "No speakers detected in %d dialogue segments", dialogue_count
        )

    passed = len(validation_errors) == 0

    await notify(
        callback, "validation", 1.0,
        f"Validation {'passed' if passed else 'failed'} "
        f"({len(validation_errors)} issues)",
    )

    return {
        "validation_passed": passed,
        "validation_errors": validation_errors,
        "validation_attempts": attempts,
    }

"""CoT batch translator node -- the core translation engine.

Groups segments into batches, sends each batch through Chain-of-Thought
translation via the LLM, and collects results.  On review re-translation
loops, only the flagged segments are re-translated.
"""
from __future__ import annotations

import logging

from fiction_translator.llm.prompts.text_utils import (
    apply_glossary_exchange,
    build_glossary_pattern,
    filter_glossary_for_batch,
    normalize_quotes,
)
from fiction_translator.pipeline.callbacks import notify
from fiction_translator.pipeline.state import (
    BatchData,
    SegmentData,
    TranslatedSegment,
    TranslationState,
)

logger = logging.getLogger(__name__)

# ── Batch grouping constants ─────────────────────────────────────────
MAX_BATCH_CHARS = 20000
MAX_BATCH_SEGMENTS = 10


async def translator_node(state: TranslationState) -> dict:
    """Translate segments in batches using Chain-of-Thought reasoning.

    If ``flagged_segments`` is non-empty (from a review loop), only those
    segments are re-translated; the rest are preserved from the previous
    iteration.
    """
    from fiction_translator.pipeline.callbacks import check_cancelled

    await check_cancelled(state)

    segments = state.get("segments", [])
    flagged_ids = state.get("flagged_segments", [])
    review_iteration = state.get("review_iteration", 0)
    review_feedback = state.get("review_feedback", [])
    previous_translations = state.get("translated_segments", [])
    callback = state.get("progress_callback")
    use_cot = state.get("use_cot", True)

    api_keys = state.get("api_keys", {})
    if not api_keys:
        raise ValueError("No API keys provided for translation")

    from fiction_translator.llm.prompts.cot_translation import (
        build_cot_translation_prompt,
        build_simple_translation_prompt,
    )
    from fiction_translator.llm.providers import get_llm_provider

    provider = get_llm_provider(
        state.get("llm_provider", "gemini"),
        api_keys=api_keys,
    )

    # Decide which segments to translate
    if flagged_ids and previous_translations:
        # Re-translation loop: only translate flagged segments
        segments_to_translate = [
            s for s in segments if s.get("order") in flagged_ids
        ]
        # Build per-segment feedback map
        feedback_by_id = {
            fb["segment_id"]: fb for fb in review_feedback
            if fb.get("segment_id") in flagged_ids
        }
    else:
        segments_to_translate = segments
        feedback_by_id = {}

    if not segments_to_translate:
        return {
            "batches": state.get("batches", []),
            "translated_segments": previous_translations,
        }

    await notify(
        callback, "translation", 0.0,
        f"Translating {len(segments_to_translate)} segments...",
    )

    # ── Group segments into batches ──────────────────────────────────
    batches_input = _group_segments_into_batches(segments_to_translate)

    glossary = state.get("glossary", {})
    glossary_pattern = build_glossary_pattern(glossary)
    personas_context = state.get("personas_context", "")
    relationships_context = state.get("relationships_context", "")
    # Combine personas and relationships context for the translator
    if relationships_context:
        personas_context = personas_context + "\n\n" + relationships_context if personas_context else relationships_context
    style_context = state.get("style_context", "")
    source_language = state.get("source_language", "ko")
    target_language = state.get("target_language", "en")

    all_batches: list[BatchData] = []
    new_translations: list[TranslatedSegment] = []
    all_unknown_terms: list[dict] = []
    total_tokens = state.get("total_tokens", 0)
    total_cost = state.get("total_cost", 0.0)

    for batch_idx, batch_segments in enumerate(batches_input):
        await check_cancelled(state)

        pct = batch_idx / max(len(batches_input), 1)
        await notify(
            callback, "translation", pct,
            f"Translating batch {batch_idx + 1}/{len(batches_input)}...",
        )

        # Build prompt segments with their IDs
        prompt_segments = []
        batch_source_texts = []
        for seg in batch_segments:
            seg_order = seg.get("order", 0)
            raw_text = normalize_quotes(seg.get("text", ""))
            batch_source_texts.append(raw_text)
            exchanged_text = apply_glossary_exchange(
                raw_text, glossary, glossary_pattern,
            )
            prompt_segments.append({
                "id": seg_order,
                "text": exchanged_text,
                "type": seg.get("type", "narrative"),
                "speaker": seg.get("speaker"),
            })

        batch_glossary = filter_glossary_for_batch(glossary, batch_source_texts)

        # Collect any feedback for segments in this batch
        batch_feedback = None
        if feedback_by_id:
            batch_feedback = [
                feedback_by_id[seg["id"]]
                for seg in prompt_segments
                if seg["id"] in feedback_by_id
            ]
            if not batch_feedback:
                batch_feedback = None

        if use_cot:
            prompt = build_cot_translation_prompt(
                segments=prompt_segments,
                source_language=source_language,
                target_language=target_language,
                glossary=batch_glossary,
                personas_context=personas_context,
                style_context=style_context,
                review_feedback=batch_feedback,
            )
        else:
            prompt = build_simple_translation_prompt(
                segments=prompt_segments,
                source_language=source_language,
                target_language=target_language,
                glossary=batch_glossary,
                personas_context=personas_context,
                style_context=style_context,
                review_feedback=batch_feedback,
            )

        try:
            result = await provider.generate_json(
                prompt=prompt,
                temperature=0.3,
                max_tokens=8192,
            )
        except Exception as e:
            logger.error("Batch %d translation failed: %s", batch_idx, e)
            # Store empty translations for failed batch
            for seg in batch_segments:
                new_translations.append(TranslatedSegment(
                    segment_id=seg.get("order", 0),
                    order=seg.get("order", 0),
                    source_text=seg.get("text", ""),
                    translated_text="[TRANSLATION FAILED]",
                    type=seg.get("type", "narrative"),
                    speaker=seg.get("speaker"),
                    translated_start_offset=0,
                    translated_end_offset=0,
                    batch_id=batch_idx,
                ))
            continue

        # Parse response
        if use_cot:
            situation_summary = result.get("situation_summary", "")
            character_events = result.get("character_events", [])
            unknown_terms_raw = result.get("unknown_terms", [])
        else:
            situation_summary = ""
            character_events = []
            unknown_terms_raw = []

        translations_raw = result.get("translations", [])

        # Build a lookup of translations by segment_id
        trans_lookup: dict[int, str] = {}
        for t in translations_raw:
            sid = t.get("segment_id")
            text = t.get("text", "")
            if sid is not None:
                trans_lookup[sid] = text

        # Fallback: if lookup missed all segments, try positional matching
        matched = sum(1 for seg in batch_segments if trans_lookup.get(seg.get("order", 0)))
        if matched == 0 and translations_raw:
            logger.warning(
                "Batch %d: segment_id mismatch. Expected orders %s, got IDs %s. "
                "Using positional fallback.",
                batch_idx,
                [s.get("order") for s in batch_segments],
                [t.get("segment_id") for t in translations_raw],
            )
            for seg, t in zip(batch_segments, translations_raw, strict=False):
                trans_lookup[seg.get("order", 0)] = t.get("text", "")

        # Create TranslatedSegment entries
        batch_seg_ids = []
        for seg in batch_segments:
            seg_order = seg.get("order", 0)
            translated_text = trans_lookup.get(seg_order, "")
            batch_seg_ids.append(seg_order)

            new_translations.append(TranslatedSegment(
                segment_id=seg_order,
                order=seg_order,
                source_text=seg.get("text", ""),
                translated_text=translated_text,
                type=seg.get("type", "narrative"),
                speaker=seg.get("speaker"),
                translated_start_offset=0,  # Computed in finalize
                translated_end_offset=0,
                batch_id=batch_idx,
            ))

        # Warn if any translations came back empty
        empty_count = sum(1 for t in new_translations[-len(batch_segments):] if not t.get("translated_text"))
        if empty_count > 0:
            logger.warning(
                "Batch %d: %d/%d segments have empty translations",
                batch_idx, empty_count, len(batch_segments),
            )

        # Collect unknown terms from this batch
        for term in unknown_terms_raw:
            if term.get("source_term") and term.get("translated_term"):
                all_unknown_terms.append(term)

        # Store batch data
        all_batches.append(BatchData(
            batch_order=batch_idx,
            segment_ids=batch_seg_ids,
            situation_summary=situation_summary,
            character_events=character_events,
            translations=[{"segment_id": t.get("segment_id"), "text": t.get("text", "")}
                          for t in translations_raw],
            review_feedback=batch_feedback,
            review_iteration=review_iteration,
        ))

    # ── Merge new translations with previous (for re-translation) ────
    if flagged_ids and previous_translations:
        # Replace only the re-translated segments
        new_ids = {t["segment_id"] for t in new_translations}
        merged = [
            t for t in previous_translations
            if t.get("segment_id") not in new_ids
        ]
        merged.extend(new_translations)
        final_translations = merged
    else:
        final_translations = new_translations

    await notify(
        callback, "translation", 1.0,
        f"Translated {len(final_translations)} segments in {len(all_batches)} batches",
    )

    return {
        "batches": all_batches,
        "translated_segments": final_translations,
        "unknown_terms": all_unknown_terms,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
    }


# ── Batch grouping ───────────────────────────────────────────────────

def _group_segments_into_batches(
    segments: list[SegmentData],
) -> list[list[SegmentData]]:
    """Group segments into batches respecting size and count limits.

    Tries to keep dialogue exchanges together: when consecutive segments
    are dialogue, they stay in the same batch if possible.

    Parameters
    ----------
    segments : list[SegmentData]
        Ordered segments to group.

    Returns
    -------
    list[list[SegmentData]]
        List of batches, each a list of segments.
    """
    if not segments:
        return []

    batches: list[list[SegmentData]] = []
    current_batch: list[SegmentData] = []
    current_chars = 0

    for seg in segments:
        seg_len = len(seg.get("text", ""))
        is_dialogue = seg.get("type") == "dialogue"

        # Check if adding this segment would exceed limits
        would_exceed_chars = (current_chars + seg_len) > MAX_BATCH_CHARS
        would_exceed_count = len(current_batch) >= MAX_BATCH_SEGMENTS

        if current_batch and (would_exceed_chars or would_exceed_count):
            # Exception: don't break up a dialogue exchange
            prev_is_dialogue = (
                current_batch
                and current_batch[-1].get("type") == "dialogue"
            )
            if is_dialogue and prev_is_dialogue and not would_exceed_chars:
                # Keep dialogue together even if count exceeded
                pass
            else:
                batches.append(current_batch)
                current_batch = []
                current_chars = 0

        current_batch.append(seg)
        current_chars += seg_len

    if current_batch:
        batches.append(current_batch)

    return batches

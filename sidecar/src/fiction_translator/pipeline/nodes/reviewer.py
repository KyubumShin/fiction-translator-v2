"""Reviewer node -- evaluates translation quality and flags segments.

Sends source/translation pairs to the LLM for quality review.  The
reviewer can flag individual segments for re-translation, triggering
the review loop (up to 2 iterations).
"""
from __future__ import annotations

import logging

from fiction_translator.pipeline.callbacks import notify
from fiction_translator.pipeline.state import TranslationState

logger = logging.getLogger(__name__)


async def reviewer_node(state: TranslationState) -> dict:
    """Review translations for quality.  Flags segments for re-translation.

    Returns review_passed, review_feedback, review_iteration, and
    flagged_segments.
    """
    from fiction_translator.pipeline.callbacks import check_cancelled

    await check_cancelled(state)

    translated_segments = state.get("translated_segments", [])
    review_iteration = state.get("review_iteration", 0) + 1
    callback = state.get("progress_callback")

    await notify(
        callback, "review", 0.0,
        f"Reviewing translations (iteration {review_iteration})...",
    )

    if not translated_segments:
        return {
            "review_passed": True,
            "review_feedback": [],
            "review_iteration": review_iteration,
            "flagged_segments": [],
        }

    api_keys = state.get("api_keys", {})
    if not api_keys:
        # No LLM available -- auto-pass
        logger.warning("No API keys for review, auto-passing")
        return {
            "review_passed": True,
            "review_feedback": [],
            "review_iteration": review_iteration,
            "flagged_segments": [],
        }

    try:
        from fiction_translator.llm.prompts.review import build_review_prompt
        from fiction_translator.llm.providers import get_llm_provider

        provider = get_llm_provider(
            state.get("llm_provider", "gemini"),
            api_keys=api_keys,
        )

        # Build review pairs
        pairs = []
        for seg in translated_segments:
            pairs.append({
                "segment_id": seg.get("segment_id", seg.get("order", 0)),
                "source_text": seg.get("source_text", ""),
                "translated_text": seg.get("translated_text", ""),
                "type": seg.get("type", "narrative"),
                "speaker": seg.get("speaker"),
            })

        # Warn if any pairs have empty translations before sending to LLM
        empty = [p["segment_id"] for p in pairs if not p.get("translated_text")]
        if empty:
            logger.warning(
                "Review: %d segments have empty translated_text: %s",
                len(empty), empty,
            )

        # Review in chunks to avoid token limits (max ~30 pairs per call)
        all_reviews: list[dict] = []
        chunk_size = 30
        overall_passed = True

        for i in range(0, len(pairs), chunk_size):
            await check_cancelled(state)

            chunk = pairs[i:i + chunk_size]
            pct = i / max(len(pairs), 1)
            await notify(
                callback, "review", pct,
                f"Reviewing segments {i+1}-{min(i+chunk_size, len(pairs))}...",
            )

            prompt = build_review_prompt(
                pairs=chunk,
                source_language=state.get("source_language", "ko"),
                target_language=state.get("target_language", "en"),
                glossary=state.get("glossary"),
                personas_context=state.get("personas_context", ""),
            )

            result = await provider.generate_json(
                prompt=prompt,
                temperature=0.2,
                max_tokens=4096,
            )

            chunk_passed = result.get("overall_passed", True)
            if not chunk_passed:
                overall_passed = False

            segment_reviews = result.get("segment_reviews", [])
            all_reviews.extend(segment_reviews)

        # Collect flagged segment IDs
        flagged: list[int] = []
        feedback: list[dict] = []

        for review in all_reviews:
            if review.get("verdict") == "flag":
                sid = review.get("segment_id")
                if sid is not None:
                    flagged.append(sid)
                    feedback.append({
                        "segment_id": sid,
                        "issue": review.get("issue", ""),
                        "suggestion": review.get("suggestion", ""),
                    })

        review_passed = overall_passed or len(flagged) == 0

        await notify(
            callback, "review", 1.0,
            f"Review {'passed' if review_passed else 'flagged ' + str(len(flagged)) + ' segments'}",
        )

        return {
            "review_passed": review_passed,
            "review_feedback": feedback,
            "review_iteration": review_iteration,
            "flagged_segments": flagged,
        }

    except Exception as e:
        logger.error("Review failed: %s", e)
        # On failure, pass through to avoid blocking the pipeline
        return {
            "review_passed": True,
            "review_feedback": [],
            "review_iteration": review_iteration,
            "flagged_segments": [],
        }

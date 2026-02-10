"""Conditional edge functions for the translation pipeline.

Each function inspects the current TranslationState and returns a string
key that LangGraph uses to pick the next node.
"""
from __future__ import annotations

from fiction_translator.pipeline.state import TranslationState


def should_re_segment(state: TranslationState) -> str:
    """After validation: re-segment on failure (up to 3 attempts), else translate.

    Returns
    -------
    "translate"  -- validation passed OR max attempts reached
    "segment"    -- validation failed and we still have retries left
    """
    if state.get("validation_passed", False):
        return "translate"
    if state.get("validation_attempts", 0) >= 3:
        # Give up and translate whatever we have
        return "translate"
    return "segment"


def should_re_translate(state: TranslationState) -> str:
    """After review: re-translate flagged segments (up to 2 iterations), else learn.

    Returns
    -------
    "learn"      -- review passed OR max review iterations reached
    "translate"  -- review flagged segments and we have retries left
    """
    if state.get("review_passed", True):
        return "learn"
    if state.get("review_iteration", 0) >= 2:
        # Max retries exhausted, proceed anyway
        return "learn"
    return "translate"

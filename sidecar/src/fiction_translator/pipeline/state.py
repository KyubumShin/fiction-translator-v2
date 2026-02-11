"""Translation pipeline state definition for LangGraph."""
from __future__ import annotations

from typing import TypedDict, Optional, Any


class SegmentData(TypedDict, total=False):
    """A single segment in the pipeline."""
    id: int | None          # DB id once saved
    order: int
    text: str
    type: str               # narrative, dialogue, action, thought
    speaker: str | None
    source_start_offset: int
    source_end_offset: int
    has_preceding_break: bool


class TranslatedSegment(TypedDict, total=False):
    """A translated segment."""
    segment_id: int
    order: int
    source_text: str
    translated_text: str
    type: str
    speaker: str | None
    translated_start_offset: int
    translated_end_offset: int
    batch_id: int | None


class BatchData(TypedDict, total=False):
    """A translation batch with CoT reasoning."""
    batch_order: int
    segment_ids: list[int]
    situation_summary: str
    character_events: list[dict]
    translations: list[dict]        # [{segment_id, text}]
    review_feedback: list[dict] | None
    review_iteration: int


class TranslationState(TypedDict, total=False):
    """Full pipeline state passed between LangGraph nodes.

    Uses total=False so nodes can return partial updates that get
    merged into the running state by LangGraph.
    """
    # ── Input ────────────────────────────────────────────────────────
    chapter_id: int
    project_id: int
    source_text: str
    source_language: str
    target_language: str
    llm_provider: str
    api_keys: dict[str, str]
    use_cot: bool

    # ── Context (loaded from DB) ─────────────────────────────────────
    glossary: dict[str, str]
    personas_context: str
    style_context: str
    existing_personas: list[dict]

    # ── Segmentation ─────────────────────────────────────────────────
    segments: list[SegmentData]

    # ── Character extraction ─────────────────────────────────────────
    detected_characters: list[dict]

    # ── Validation ───────────────────────────────────────────────────
    validation_passed: bool
    validation_errors: list[str]
    validation_attempts: int

    # ── Translation ──────────────────────────────────────────────────
    batches: list[BatchData]
    translated_segments: list[TranslatedSegment]

    # ── Review ───────────────────────────────────────────────────────
    review_passed: bool
    review_feedback: list[dict]
    review_iteration: int
    flagged_segments: list[int]     # segment IDs that need re-translation

    # ── Persona learning ─────────────────────────────────────────────
    persona_suggestions: list[dict]

    # ── Unknown terms ─────────────────────────────────────────────────
    unknown_terms: list[dict]

    # ── Output ───────────────────────────────────────────────────────
    connected_translated_text: str
    segment_map: list[dict]

    # ── Pipeline metadata ────────────────────────────────────────────
    pipeline_run_id: int | None
    progress_callback: Any          # async callable(stage, pct, msg)
    error: str | None
    total_tokens: int
    total_cost: float

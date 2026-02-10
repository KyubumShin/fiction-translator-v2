"""LangGraph pipeline definition -- wires all nodes and edges together.

Exports:
    build_translation_graph()   -- returns an uncompiled StateGraph
    get_translation_graph()     -- returns a compiled, cached graph
    run_translation_pipeline()  -- high-level entry point
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from langgraph.graph import StateGraph, END

from fiction_translator.pipeline.state import TranslationState
from fiction_translator.pipeline.callbacks import notify
from fiction_translator.pipeline.edges import (
    should_re_segment,
    should_re_translate,
)
from fiction_translator.pipeline.nodes.segmenter import segmenter_node
from fiction_translator.pipeline.nodes.character_extractor import (
    character_extractor_node,
)
from fiction_translator.pipeline.nodes.validator import validator_node
from fiction_translator.pipeline.nodes.translator import translator_node
from fiction_translator.pipeline.nodes.reviewer import reviewer_node
from fiction_translator.pipeline.nodes.persona_learner import (
    persona_learner_node,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Inline nodes (load_context, finalize) -- thin DB integration layers
# ─────────────────────────────────────────────────────────────────────

async def load_context_node(state: TranslationState) -> dict:
    """Load project glossary, personas, and settings from the database."""
    callback = state.get("progress_callback")
    await notify(callback, "load_context", 0.0, "Loading project context...")

    from fiction_translator.db.session import get_db
    from fiction_translator.services.glossary_service import get_glossary_map
    from fiction_translator.services.persona_service import (
        get_personas_context,
        list_personas,
    )

    db = get_db()
    try:
        project_id = state["project_id"]
        glossary = get_glossary_map(db, project_id)
        personas_ctx = get_personas_context(db, project_id)
        existing = list_personas(db, project_id)

        await notify(
            callback, "load_context", 1.0,
            f"Loaded {len(glossary)} glossary terms, {len(existing)} personas",
        )

        return {
            "glossary": glossary,
            "personas_context": personas_ctx,
            "existing_personas": existing,
        }
    finally:
        db.close()


async def finalize_node(state: TranslationState) -> dict:
    """Join translated segments into connected prose, save to DB.

    Also persists individual segments and translations to the database
    so the editor can display them with click-to-highlight.
    """
    callback = state.get("progress_callback")
    await notify(callback, "finalize", 0.0, "Finalising translation...")

    translated_segments = state.get("translated_segments", [])
    segments = state.get("segments", [])
    chapter_id = state["chapter_id"]
    target_language = state.get("target_language", "en")

    # Sort by order
    sorted_segs = sorted(
        translated_segments,
        key=lambda s: s.get("segment_id", s.get("order", 0)),
    )

    # Build connected text and segment map with translated offsets
    parts: list[str] = []
    offset = 0
    segment_map: list[dict] = []

    for seg in sorted_segs:
        text = seg.get("translated_text", "")
        start = offset
        end = offset + len(text)

        # Find matching source segment for offsets
        source_start = 0
        source_end = 0
        seg_id = seg.get("segment_id", seg.get("order", 0))
        for src_seg in segments:
            if src_seg.get("order") == seg_id:
                source_start = src_seg.get("source_start_offset", 0)
                source_end = src_seg.get("source_end_offset", 0)
                break

        segment_map.append({
            "segment_id": seg_id,
            "source_start": source_start,
            "source_end": source_end,
            "translated_start": start,
            "translated_end": end,
            "type": seg.get("type", "narrative"),
            "speaker": seg.get("speaker"),
            "batch_id": seg.get("batch_id"),
        })

        parts.append(text)
        offset = end + 1  # +1 for newline separator

    connected = "\n".join(parts)

    # ── Persist to database ──────────────────────────────────────────
    from fiction_translator.db.session import get_db
    from fiction_translator.db.models import (
        Chapter, Segment, Translation, TranslationBatch,
        TranslationStatus, PersonaSuggestion, Persona, GlossaryEntry,
    )

    db = get_db()
    try:
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if not chapter:
            raise ValueError(f"Chapter {chapter_id} not found")

        # Save connected translated text
        chapter.translated_content = connected
        chapter.translation_stale = False

        # Clear previous segments for this chapter (full re-translation)
        db.query(Translation).filter(
            Translation.segment_id.in_(
                db.query(Segment.id).filter(Segment.chapter_id == chapter_id)
            )
        ).delete(synchronize_session="fetch")
        db.query(Segment).filter(Segment.chapter_id == chapter_id).delete(
            synchronize_session="fetch"
        )

        # Save segments and translations
        for i, src_seg in enumerate(segments):
            db_seg = Segment(
                chapter_id=chapter_id,
                order=src_seg.get("order", i),
                source_text=src_seg.get("text", ""),
                source_start_offset=src_seg.get("source_start_offset"),
                source_end_offset=src_seg.get("source_end_offset"),
                segment_type=src_seg.get("type", "narrative"),
                speaker=src_seg.get("speaker"),
                status=TranslationStatus.TRANSLATED,
            )
            db.add(db_seg)
            db.flush()  # Get the ID

            # Find matching translation
            seg_order = src_seg.get("order", i)
            matching_trans = None
            for ts in sorted_segs:
                if ts.get("segment_id", ts.get("order")) == seg_order:
                    matching_trans = ts
                    break

            if matching_trans:
                # Find translated offsets from segment_map
                trans_start = 0
                trans_end = 0
                for sm in segment_map:
                    if sm["segment_id"] == seg_order:
                        trans_start = sm["translated_start"]
                        trans_end = sm["translated_end"]
                        break

                db_trans = Translation(
                    segment_id=db_seg.id,
                    target_language=target_language,
                    translated_text=matching_trans.get("translated_text", ""),
                    translated_start_offset=trans_start,
                    translated_end_offset=trans_end,
                    status=TranslationStatus.TRANSLATED,
                    batch_id=None,  # Will link to batch if we save batches
                )
                db.add(db_trans)

        # Save translation batches and build batch_order -> db_id mapping
        batches = state.get("batches", [])
        batch_order_to_id: dict[int, int] = {}
        for batch_data in batches:
            db_batch = TranslationBatch(
                chapter_id=chapter_id,
                target_language=target_language,
                batch_order=batch_data.get("batch_order", 0),
                situation_summary=batch_data.get("situation_summary"),
                character_events=batch_data.get("character_events"),
                full_cot_json={
                    "situation_summary": batch_data.get("situation_summary"),
                    "character_events": batch_data.get("character_events"),
                    "translations": batch_data.get("translations"),
                },
                segment_ids=batch_data.get("segment_ids"),
                review_feedback=batch_data.get("review_feedback"),
                review_iteration=batch_data.get("review_iteration", 0),
            )
            db.add(db_batch)
            db.flush()
            batch_order_to_id[batch_data.get("batch_order", 0)] = db_batch.id

        # Link translations to their batch records
        if batch_order_to_id:
            # Build segment_order -> batch_db_id mapping from batch data
            seg_to_batch_db_id: dict[int, int] = {}
            for batch_data in batches:
                db_batch_id = batch_order_to_id.get(batch_data.get("batch_order", 0))
                if db_batch_id:
                    for seg_id in (batch_data.get("segment_ids") or []):
                        seg_to_batch_db_id[seg_id] = db_batch_id

            # Update translations with correct batch_id
            for trans in db.query(Translation).filter(
                Translation.segment_id.in_(
                    db.query(Segment.id).filter(Segment.chapter_id == chapter_id)
                )
            ).all():
                seg = db.query(Segment).filter(Segment.id == trans.segment_id).first()
                if seg and seg.order in seg_to_batch_db_id:
                    trans.batch_id = seg_to_batch_db_id[seg.order]

        # Save persona suggestions
        persona_suggestions = state.get("persona_suggestions", [])
        for suggestion in persona_suggestions:
            persona_id = suggestion.get("persona_id")
            if persona_id is None:
                # Create new persona for unknown character
                new_persona = Persona(
                    project_id=chapter.project_id,
                    name=suggestion.get("name", "Unknown"),
                    auto_detected=True,
                    detection_confidence=suggestion.get("confidence"),
                )
                db.add(new_persona)
                db.flush()
                persona_id = new_persona.id

            db_suggestion = PersonaSuggestion(
                persona_id=persona_id,
                field_name=suggestion.get("field", ""),
                suggested_value=suggestion.get("value", ""),
                confidence=suggestion.get("confidence"),
                status="pending",
            )
            db.add(db_suggestion)

        # Save unknown terms as auto-detected glossary entries
        unknown_terms = state.get("unknown_terms", [])
        if unknown_terms:
            existing_terms = {
                e.source_term.lower()
                for e in db.query(GlossaryEntry).filter(
                    GlossaryEntry.project_id == chapter.project_id
                ).all()
            }
            for term in unknown_terms:
                source = term.get("source_term", "").strip()
                translated = term.get("translated_term", "").strip()
                if source and translated and source.lower() not in existing_terms:
                    db.add(GlossaryEntry(
                        project_id=chapter.project_id,
                        source_term=source,
                        translated_term=translated,
                        term_type=term.get("term_type", "general"),
                        auto_detected=True,
                    ))
                    existing_terms.add(source.lower())

        db.commit()

        await notify(callback, "finalize", 1.0, "Translation saved to database")

    finally:
        db.close()

    return {
        "connected_translated_text": connected,
        "segment_map": segment_map,
    }


# ─────────────────────────────────────────────────────────────────────
# Graph construction
# ─────────────────────────────────────────────────────────────────────

def build_translation_graph() -> StateGraph:
    """Build the LangGraph translation pipeline.

    Pipeline flow::

        load_context -> segment -> extract_characters -> validate
            validate --[pass]--> translate
            validate --[fail, attempts < 3]--> segment
        translate -> review
            review --[pass]--> learn_personas
            review --[fail, iteration < 2]--> translate
        learn_personas -> finalize -> END
    """
    graph = StateGraph(TranslationState)

    # Add nodes
    graph.add_node("load_context", load_context_node)
    graph.add_node("segment", segmenter_node)
    graph.add_node("extract_characters", character_extractor_node)
    graph.add_node("validate", validator_node)
    graph.add_node("translate", translator_node)
    graph.add_node("review", reviewer_node)
    graph.add_node("learn_personas", persona_learner_node)
    graph.add_node("finalize", finalize_node)

    # Linear edges
    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "segment")
    graph.add_edge("segment", "extract_characters")
    graph.add_edge("extract_characters", "validate")

    # Conditional: validation gate
    graph.add_conditional_edges("validate", should_re_segment, {
        "segment": "segment",
        "translate": "translate",
    })

    # Linear: translate -> review
    graph.add_edge("translate", "review")

    # Conditional: review loop
    graph.add_conditional_edges("review", should_re_translate, {
        "translate": "translate",
        "learn": "learn_personas",
    })

    # Linear: learn -> finalize -> END
    graph.add_edge("learn_personas", "finalize")
    graph.add_edge("finalize", END)

    return graph


# ─────────────────────────────────────────────────────────────────────
# Compiled graph singleton
# ─────────────────────────────────────────────────────────────────────

_compiled_graph = None


def get_translation_graph():
    """Get (or create) the compiled translation pipeline graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_translation_graph().compile()
    return _compiled_graph


# ─────────────────────────────────────────────────────────────────────
# High-level entry point
# ─────────────────────────────────────────────────────────────────────

async def run_translation_pipeline(
    db,
    chapter_id: int,
    target_language: str = "en",
    api_keys: dict | None = None,
    progress_callback=None,
    **kwargs,
) -> dict:
    """Run the full translation pipeline for a chapter.

    Parameters
    ----------
    db : Session
        SQLAlchemy database session.
    chapter_id : int
        ID of the chapter to translate.
    target_language : str
        Target language code (default: ``"en"``).
    api_keys : dict | None
        Provider API keys, e.g. ``{"gemini": "...", "openai": "..."}``.
    progress_callback : callable | None
        ``async def callback(stage, pct, message)``
    **kwargs
        Extra overrides merged into the initial state.

    Returns
    -------
    dict
        Result with ``success``, ``pipeline_run_id``, ``connected_translated_text``,
        ``segment_map``, ``persona_suggestions``, and ``stats``.
    """
    from fiction_translator.db.models import Chapter, PipelineRun, PipelineStatus

    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")

    project = chapter.project

    # Create pipeline run record
    run = PipelineRun(
        chapter_id=chapter_id,
        target_language=target_language,
        status=PipelineStatus.RUNNING,
        started_at=datetime.utcnow(),
        config={
            "llm_provider": project.llm_provider,
            "target_language": target_language,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    initial_state: TranslationState = {
        "chapter_id": chapter_id,
        "project_id": project.id,
        "source_text": chapter.source_content or "",
        "source_language": project.source_language,
        "target_language": target_language,
        "llm_provider": project.llm_provider or "gemini",
        "api_keys": api_keys or {},
        "pipeline_run_id": run.id,
        "progress_callback": progress_callback,
        "validation_attempts": 0,
        "review_iteration": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
    }
    # Merge any extra overrides
    initial_state.update(kwargs)  # type: ignore[arg-type]

    try:
        graph = get_translation_graph()
        result = await graph.ainvoke(initial_state)

        # Update pipeline run
        run.status = PipelineStatus.COMPLETED
        run.completed_at = datetime.utcnow()
        run.stats = {
            "segments": len(result.get("segments", [])),
            "batches": len(result.get("batches", [])),
            "total_tokens": result.get("total_tokens", 0),
            "persona_suggestions": len(result.get("persona_suggestions", [])),
            "review_iterations": result.get("review_iteration", 0),
            "validation_attempts": result.get("validation_attempts", 0),
        }
        db.commit()

        return {
            "success": True,
            "pipeline_run_id": run.id,
            "connected_translated_text": result.get("connected_translated_text", ""),
            "segment_map": result.get("segment_map", []),
            "persona_suggestions": result.get("persona_suggestions", []),
            "stats": run.stats,
        }

    except Exception as e:
        logger.error("Pipeline failed for chapter %d: %s", chapter_id, e)
        run.status = PipelineStatus.FAILED
        run.completed_at = datetime.utcnow()
        run.error_message = str(e)
        db.commit()
        raise

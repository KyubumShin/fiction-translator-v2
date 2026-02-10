"""Segment re-translation service."""
from __future__ import annotations

import logging
from sqlalchemy.orm import Session

from fiction_translator.db.models import Segment, Translation, Project, TranslationStatus
from fiction_translator.services.glossary_service import get_glossary_map
from fiction_translator.services.persona_service import get_personas_context
from fiction_translator.llm.prompts.cot_translation import build_cot_translation_prompt
from fiction_translator.llm.providers import get_llm_provider

logger = logging.getLogger(__name__)


async def retranslate_segments(
    db: Session,
    segment_ids: list[int],
    target_language: str,
    user_guide: str,
    api_keys: dict,
) -> dict:
    """Re-translate specific segments with user-provided guidance.

    Parameters
    ----------
    db : Session
        Database session.
    segment_ids : list[int]
        IDs of segments to re-translate.
    target_language : str
        Target language code.
    user_guide : str
        User instructions to guide the translation.
    api_keys : dict
        API keys for LLM providers.

    Returns
    -------
    dict
        Result with updated translation data.
    """
    if not segment_ids:
        raise ValueError("No segment IDs provided")

    # Load segments
    segments = db.query(Segment).filter(Segment.id.in_(segment_ids)).all()
    if not segments:
        raise ValueError("No segments found for the given IDs")

    # Get project context from the first segment's chapter
    chapter = segments[0].chapter
    project = chapter.project

    # Build segment dicts for prompt
    seg_dicts = []
    for seg in segments:
        seg_dicts.append({
            "id": seg.id,
            "text": seg.source_text,
            "type": seg.segment_type,
            "speaker": seg.speaker,
        })

    # Load project context
    glossary = get_glossary_map(db, project.id)
    personas_context = get_personas_context(db, project.id)

    # Build prompt with user guide
    prompt = build_cot_translation_prompt(
        segments=seg_dicts,
        source_language=project.source_language,
        target_language=target_language,
        glossary=glossary if glossary else None,
        personas_context=personas_context,
        user_guide=user_guide,
    )

    # Call LLM
    provider = get_llm_provider(project.llm_provider, api_keys=api_keys)
    result = await provider.generate_json(prompt, max_tokens=4096)

    # Update translations
    translations_data = result.get("translations", [])
    updated = []
    for t_data in translations_data:
        seg_id = t_data.get("segment_id")
        new_text = t_data.get("text", "")
        if not seg_id or not new_text:
            continue

        translation = db.query(Translation).filter(
            Translation.segment_id == seg_id,
            Translation.target_language == target_language,
        ).first()

        if translation:
            translation.translated_text = new_text
            translation.status = TranslationStatus.TRANSLATED
            translation.manually_edited = False
            updated.append({"segment_id": seg_id, "translated_text": new_text})
        else:
            # Create new translation record if none exists
            translation = Translation(
                segment_id=seg_id,
                target_language=target_language,
                translated_text=new_text,
                status=TranslationStatus.TRANSLATED,
            )
            db.add(translation)
            updated.append({"segment_id": seg_id, "translated_text": new_text})

    db.commit()

    return {
        "success": True,
        "updated_count": len(updated),
        "translations": updated,
    }

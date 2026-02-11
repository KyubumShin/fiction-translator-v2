"""Chapter CRUD service with editor data support."""
from __future__ import annotations

import re

from sqlalchemy.orm import Session
from sqlalchemy import func
from fiction_translator.db.models import Chapter, Segment, Translation, TranslationStatus


def list_chapters(db: Session, project_id: int) -> list[dict]:
    """List all chapters in a project with statistics."""
    chapters = db.query(Chapter).filter(
        Chapter.project_id == project_id
    ).order_by(Chapter.order).all()
    result = []
    for ch in chapters:
        seg_count = db.query(func.count(Segment.id)).filter(Segment.chapter_id == ch.id).scalar()
        # Count translations that are not pending
        trans_count = db.query(func.count(Translation.id)).filter(
            Translation.segment_id.in_(
                db.query(Segment.id).filter(Segment.chapter_id == ch.id)
            ),
            Translation.status != TranslationStatus.PENDING,
        ).scalar()
        result.append({
            **_chapter_to_dict(ch),
            "segment_count": seg_count,
            "translated_count": trans_count,
        })
    return result


def create_chapter(db: Session, project_id: int, title: str, source_content: str = "", **kwargs) -> dict:
    """Create a new chapter."""
    # Get next order number
    max_order = db.query(func.max(Chapter.order)).filter(
        Chapter.project_id == project_id
    ).scalar() or 0

    chapter = Chapter(
        project_id=project_id,
        title=title,
        order=max_order + 1,
        source_content=source_content,
        file_path=kwargs.get("file_path"),
    )
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return _chapter_to_dict(chapter)


def get_chapter(db: Session, chapter_id: int) -> dict:
    """Get a single chapter by ID."""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")
    return _chapter_to_dict(chapter)


def update_chapter(db: Session, chapter_id: int, **kwargs) -> dict:
    """Update an existing chapter."""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")
    for key, value in kwargs.items():
        if hasattr(chapter, key) and key != "id":
            setattr(chapter, key, value)
    db.commit()
    db.refresh(chapter)
    return _chapter_to_dict(chapter)


def delete_chapter(db: Session, chapter_id: int) -> dict:
    """Delete a chapter and all related data (cascades)."""
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")
    db.delete(chapter)
    db.commit()
    return {"deleted": True, "id": chapter_id}


def get_editor_data(db: Session, chapter_id: int, target_language: str = "en") -> dict:
    """Get connected text view data for the editor.

    Returns source text and translated text as continuous prose,
    with a segment map for click-to-highlight linking.
    """
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise ValueError(f"Chapter {chapter_id} not found")

    segments = db.query(Segment).filter(
        Segment.chapter_id == chapter_id
    ).order_by(Segment.order).all()

    if not segments:
        return {
            "source_connected_text": chapter.source_content or "",
            "translated_connected_text": chapter.translated_content or "",
            "segment_map": [],
        }

    source_content = chapter.source_content or ""

    # Build translation lookup (one query per segment, cached)
    translation_map: dict[int, "Translation | None"] = {}
    for seg in segments:
        translation_map[seg.id] = db.query(Translation).filter(
            Translation.segment_id == seg.id,
            Translation.target_language == target_language,
        ).first()

    # Phase 1: Determine paragraph breaks between segments
    has_break_list: list[bool] = [False]  # first segment never has a preceding break

    for i in range(1, len(segments)):
        prev_end = segments[i - 1].source_end_offset
        curr_start = segments[i].source_start_offset

        has_break = False
        if prev_end is not None and curr_start is not None and prev_end <= curr_start:
            gap = source_content[prev_end:curr_start]
            has_break = bool(re.search(r'\n\s*\n', gap))
        has_break_list.append(has_break)

    # Phase 2: Build source connected text with variable separators
    source_parts: list[str] = []
    source_offset = 0
    source_starts: list[int] = []
    source_ends: list[int] = []

    for i, seg in enumerate(segments):
        source_text = seg.source_text

        if i > 0:
            separator = "\n\n" if has_break_list[i] else "\n"
            source_parts.append(separator)
            source_offset += len(separator)

        source_start = source_offset
        source_end = source_offset + len(source_text)
        source_starts.append(source_start)
        source_ends.append(source_end)

        source_parts.append(source_text)
        source_offset = source_end

    source_connected = "".join(source_parts)

    # Phase 3: Build translated connected text with variable separators
    translated_parts: list[str] = []
    translated_offset = 0
    translated_starts: list[int] = []
    translated_ends: list[int] = []

    for i, seg in enumerate(segments):
        translation = translation_map.get(seg.id)
        translated_text = translation.translated_text if translation and translation.translated_text else ""

        if i > 0 and translated_text and translated_parts:
            separator = "\n\n" if has_break_list[i] else "\n"
            translated_parts.append(separator)
            translated_offset += len(separator)

        translated_start = translated_offset
        translated_end = translated_offset + len(translated_text)
        translated_starts.append(translated_start)
        translated_ends.append(translated_end)

        if translated_text:
            translated_parts.append(translated_text)
            translated_offset = translated_end

    translated_connected = "".join(translated_parts)

    # Phase 4: Build segment_map
    segment_map = []
    for i, seg in enumerate(segments):
        translation = translation_map.get(seg.id)

        segment_map.append({
            "segment_id": seg.id,
            "source_start": source_starts[i],
            "source_end": source_ends[i],
            "translated_start": translated_starts[i],
            "translated_end": translated_ends[i],
            "type": seg.segment_type,
            "speaker": seg.speaker,
            "batch_id": translation.batch_id if translation else None,
        })

    return {
        "source_connected_text": source_connected,
        "translated_connected_text": translated_connected,
        "segment_map": segment_map,
    }


def _chapter_to_dict(ch: Chapter) -> dict:
    """Convert Chapter model to dict."""
    return {
        "id": ch.id,
        "project_id": ch.project_id,
        "title": ch.title,
        "order": ch.order,
        "source_content": ch.source_content,
        "file_path": ch.file_path,
        "translated_content": ch.translated_content,
        "translation_stale": ch.translation_stale,
        "created_at": ch.created_at.isoformat() if ch.created_at else None,
        "updated_at": ch.updated_at.isoformat() if ch.updated_at else None,
    }

"""Chapter CRUD service with editor data support."""
from __future__ import annotations

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

    # Build connected text from segments
    source_parts = []
    translated_parts = []
    segment_map = []

    source_offset = 0
    translated_offset = 0

    for seg in segments:
        source_text = seg.source_text

        # Get translation for this segment
        translation = db.query(Translation).filter(
            Translation.segment_id == seg.id,
            Translation.target_language == target_language,
        ).first()

        translated_text = translation.translated_text if translation and translation.translated_text else ""

        # Track offsets
        source_start = source_offset
        source_end = source_offset + len(source_text)
        translated_start = translated_offset
        translated_end = translated_offset + len(translated_text)

        segment_map.append({
            "segment_id": seg.id,
            "source_start": source_start,
            "source_end": source_end,
            "translated_start": translated_start,
            "translated_end": translated_end,
            "type": seg.segment_type,
            "speaker": seg.speaker,
            "batch_id": translation.batch_id if translation else None,
        })

        source_parts.append(source_text)
        if translated_text:
            translated_parts.append(translated_text)

        # Add separator (newline between segments for prose flow)
        source_offset = source_end + 1  # +1 for newline
        translated_offset = translated_end + (1 if translated_text else 0)

    source_connected = "\n".join(source_parts)
    translated_connected = "\n".join(translated_parts)

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

"""Glossary CRUD service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from fiction_translator.db.models import GlossaryEntry

_GLOSSARY_UPDATABLE = {"source_term", "translated_term", "term_type", "notes", "context"}


def list_glossary(db: Session, project_id: int) -> list[dict]:
    """List all glossary entries for a project."""
    entries = db.query(GlossaryEntry).filter(
        GlossaryEntry.project_id == project_id
    ).order_by(GlossaryEntry.source_term).all()
    return [_entry_to_dict(e) for e in entries]


def create_glossary_entry(db: Session, project_id: int, source_term: str, translated_term: str, **kwargs) -> dict:
    """Create a new glossary entry."""
    entry = GlossaryEntry(
        project_id=project_id,
        source_term=source_term,
        translated_term=translated_term,
        term_type=kwargs.get("term_type", "general"),
        notes=kwargs.get("notes"),
        context=kwargs.get("context"),
        auto_detected=kwargs.get("auto_detected", False),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _entry_to_dict(entry)


def get_glossary_entry(db: Session, entry_id: int) -> dict:
    """Get a single glossary entry by ID."""
    entry = db.query(GlossaryEntry).filter(GlossaryEntry.id == entry_id).first()
    if not entry:
        raise ValueError(f"Glossary entry {entry_id} not found")
    return _entry_to_dict(entry)


def update_glossary_entry(db: Session, entry_id: int, **kwargs) -> dict:
    """Update an existing glossary entry."""
    entry = db.query(GlossaryEntry).filter(GlossaryEntry.id == entry_id).first()
    if not entry:
        raise ValueError(f"Glossary entry {entry_id} not found")
    for key, value in kwargs.items():
        if key in _GLOSSARY_UPDATABLE:
            setattr(entry, key, value)
    db.commit()
    db.refresh(entry)
    return _entry_to_dict(entry)


def delete_glossary_entry(db: Session, entry_id: int) -> dict:
    """Delete a glossary entry."""
    entry = db.query(GlossaryEntry).filter(GlossaryEntry.id == entry_id).first()
    if not entry:
        raise ValueError(f"Glossary entry {entry_id} not found")
    db.delete(entry)
    db.commit()
    return {"deleted": True, "id": entry_id}


def get_glossary_map(db: Session, project_id: int) -> dict[str, str]:
    """Get glossary as source->target mapping for translation prompts."""
    entries = db.query(GlossaryEntry).filter(
        GlossaryEntry.project_id == project_id
    ).all()
    return {e.source_term: e.translated_term for e in entries}


def bulk_import(db: Session, project_id: int, entries: list[dict]) -> dict:
    """Import multiple glossary entries."""
    created = 0
    for entry_data in entries:
        entry = GlossaryEntry(
            project_id=project_id,
            source_term=entry_data["source_term"],
            translated_term=entry_data["translated_term"],
            term_type=entry_data.get("term_type", "general"),
            notes=entry_data.get("notes"),
            context=entry_data.get("context"),
            auto_detected=entry_data.get("auto_detected", False),
        )
        db.add(entry)
        created += 1
    db.commit()
    return {"imported": created}


def _entry_to_dict(e: GlossaryEntry) -> dict:
    """Convert GlossaryEntry model to dict."""
    return {
        "id": e.id,
        "project_id": e.project_id,
        "source_term": e.source_term,
        "translated_term": e.translated_term,
        "term_type": e.term_type,
        "notes": e.notes,
        "context": e.context,
        "auto_detected": e.auto_detected,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }

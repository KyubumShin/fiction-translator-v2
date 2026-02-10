"""Persona CRUD service."""
from __future__ import annotations

from sqlalchemy.orm import Session
from fiction_translator.db.models import Persona, PersonaSuggestion


def list_personas(db: Session, project_id: int) -> list[dict]:
    """List all personas in a project, ordered by appearance count."""
    personas = db.query(Persona).filter(
        Persona.project_id == project_id
    ).order_by(Persona.appearance_count.desc()).all()
    return [_persona_to_dict(p) for p in personas]


def create_persona(db: Session, project_id: int, name: str, **kwargs) -> dict:
    """Create a new persona."""
    persona = Persona(
        project_id=project_id,
        name=name,
        aliases=kwargs.get("aliases"),
        personality=kwargs.get("personality"),
        speech_style=kwargs.get("speech_style"),
        formality_level=kwargs.get("formality_level", 3),
        age_group=kwargs.get("age_group"),
        example_dialogues=kwargs.get("example_dialogues"),
        notes=kwargs.get("notes"),
        auto_detected=kwargs.get("auto_detected", False),
        detection_confidence=kwargs.get("detection_confidence"),
        source_chapter_id=kwargs.get("source_chapter_id"),
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return _persona_to_dict(persona)


def get_persona(db: Session, persona_id: int) -> dict:
    """Get a single persona by ID."""
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise ValueError(f"Persona {persona_id} not found")
    return _persona_to_dict(persona)


def update_persona(db: Session, persona_id: int, **kwargs) -> dict:
    """Update an existing persona."""
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise ValueError(f"Persona {persona_id} not found")
    for key, value in kwargs.items():
        if hasattr(persona, key) and key != "id":
            setattr(persona, key, value)
    db.commit()
    db.refresh(persona)
    return _persona_to_dict(persona)


def delete_persona(db: Session, persona_id: int) -> dict:
    """Delete a persona and all suggestions (cascades)."""
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if not persona:
        raise ValueError(f"Persona {persona_id} not found")
    db.delete(persona)
    db.commit()
    return {"deleted": True, "id": persona_id}


def get_personas_context(db: Session, project_id: int) -> str:
    """Generate persona context string for translation prompts."""
    personas = db.query(Persona).filter(Persona.project_id == project_id).all()
    if not personas:
        return ""

    parts = ["## Character Voice Guide\n"]
    for p in personas:
        part = f"### {p.name}"
        if p.aliases:
            part += f" (also: {', '.join(p.aliases)})"
        part += "\n"
        if p.personality:
            part += f"- Personality: {p.personality}\n"
        if p.speech_style:
            part += f"- Speech style: {p.speech_style}\n"
        formality_labels = {1: "very casual", 2: "casual", 3: "neutral", 4: "formal", 5: "very formal"}
        part += f"- Formality: {formality_labels.get(p.formality_level, 'neutral')}\n"
        if p.age_group:
            part += f"- Age group: {p.age_group}\n"
        parts.append(part)
    return "\n".join(parts)


def list_suggestions(db: Session, persona_id: int) -> list[dict]:
    """List all pending suggestions for a persona."""
    suggestions = db.query(PersonaSuggestion).filter(
        PersonaSuggestion.persona_id == persona_id,
        PersonaSuggestion.status == "pending",
    ).all()
    return [{
        "id": s.id,
        "persona_id": s.persona_id,
        "field_name": s.field_name,
        "suggested_value": s.suggested_value,
        "confidence": s.confidence,
        "status": s.status,
        "source_batch_id": s.source_batch_id,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    } for s in suggestions]


def apply_suggestion(db: Session, suggestion_id: int, approve: bool = True) -> dict:
    """Approve or reject a persona suggestion."""
    suggestion = db.query(PersonaSuggestion).filter(PersonaSuggestion.id == suggestion_id).first()
    if not suggestion:
        raise ValueError(f"Suggestion {suggestion_id} not found")

    if approve:
        persona = db.query(Persona).filter(Persona.id == suggestion.persona_id).first()
        if persona and hasattr(persona, suggestion.field_name):
            current = getattr(persona, suggestion.field_name)
            # Handle list fields (aliases, example_dialogues)
            if isinstance(current, list):
                if suggestion.suggested_value not in current:
                    current.append(suggestion.suggested_value)
                    setattr(persona, suggestion.field_name, current)
            # Handle string fields
            elif isinstance(current, str):
                if current:
                    setattr(persona, suggestion.field_name, f"{current}; {suggestion.suggested_value}")
                else:
                    setattr(persona, suggestion.field_name, suggestion.suggested_value)
            else:
                setattr(persona, suggestion.field_name, suggestion.suggested_value)
        suggestion.status = "approved"
    else:
        suggestion.status = "rejected"

    db.commit()
    return {"id": suggestion.id, "status": suggestion.status}


def increment_appearance(db: Session, persona_id: int, chapter_id: int):
    """Increment appearance count and update last seen chapter."""
    persona = db.query(Persona).filter(Persona.id == persona_id).first()
    if persona:
        persona.appearance_count = (persona.appearance_count or 0) + 1
        persona.last_seen_chapter_id = chapter_id
        db.commit()


def _persona_to_dict(p: Persona) -> dict:
    """Convert Persona model to dict."""
    return {
        "id": p.id,
        "project_id": p.project_id,
        "name": p.name,
        "aliases": p.aliases,
        "personality": p.personality,
        "speech_style": p.speech_style,
        "formality_level": p.formality_level,
        "age_group": p.age_group,
        "example_dialogues": p.example_dialogues,
        "notes": p.notes,
        "auto_detected": p.auto_detected,
        "detection_confidence": p.detection_confidence,
        "source_chapter_id": p.source_chapter_id,
        "appearance_count": p.appearance_count,
        "last_seen_chapter_id": p.last_seen_chapter_id,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }

"""Character relationship CRUD service."""
from __future__ import annotations

from sqlalchemy.orm import Session

from fiction_translator.db.models import CharacterRelationship, Persona

_RELATIONSHIP_UPDATABLE = {"relationship_type", "description", "intimacy_level"}


def list_relationships(db: Session, project_id: int) -> list[dict]:
    """List all relationships in a project."""
    relationships = db.query(CharacterRelationship).filter(
        CharacterRelationship.project_id == project_id
    ).all()
    return [_relationship_to_dict(r) for r in relationships]


def create_relationship(
    db: Session, project_id: int, persona_id_1: int, persona_id_2: int, **kwargs
) -> dict:
    """Create a new relationship between two personas.

    Normalises the pair so persona_id_1 < persona_id_2.
    """
    # Normalize pair ordering
    if persona_id_1 > persona_id_2:
        persona_id_1, persona_id_2 = persona_id_2, persona_id_1

    if persona_id_1 == persona_id_2:
        raise ValueError("Cannot create a relationship between a persona and itself")

    rel = CharacterRelationship(
        project_id=project_id,
        persona_id_1=persona_id_1,
        persona_id_2=persona_id_2,
        relationship_type=kwargs.get("relationship_type", "acquaintance"),
        description=kwargs.get("description"),
        intimacy_level=kwargs.get("intimacy_level", 5),
        auto_detected=kwargs.get("auto_detected", False),
        detection_confidence=kwargs.get("detection_confidence"),
    )
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return _relationship_to_dict(rel)


def update_relationship(db: Session, relationship_id: int, **kwargs) -> dict:
    """Update an existing relationship."""
    rel = db.query(CharacterRelationship).filter(
        CharacterRelationship.id == relationship_id
    ).first()
    if not rel:
        raise ValueError(f"Relationship {relationship_id} not found")
    for key, value in kwargs.items():
        if key in _RELATIONSHIP_UPDATABLE:
            setattr(rel, key, value)
    db.commit()
    db.refresh(rel)
    return _relationship_to_dict(rel)


def delete_relationship(db: Session, relationship_id: int) -> dict:
    """Delete a relationship."""
    rel = db.query(CharacterRelationship).filter(
        CharacterRelationship.id == relationship_id
    ).first()
    if not rel:
        raise ValueError(f"Relationship {relationship_id} not found")
    db.delete(rel)
    db.commit()
    return {"deleted": True, "id": relationship_id}


def get_relationships_context(db: Session, project_id: int) -> str:
    """Generate relationship context string for translation prompts."""
    relationships = db.query(CharacterRelationship).filter(
        CharacterRelationship.project_id == project_id
    ).all()
    if not relationships:
        return ""

    parts = ["## Character Relationships\n"]
    for r in relationships:
        p1 = db.query(Persona).filter(Persona.id == r.persona_id_1).first()
        p2 = db.query(Persona).filter(Persona.id == r.persona_id_2).first()
        if not p1 or not p2:
            continue
        line = (
            f"- {p1.name} ↔ {p2.name}: {r.relationship_type} "
            f"(intimacy: {r.intimacy_level}/10)"
        )
        if r.description:
            line += f" - {r.description}"
        parts.append(line)
    return "\n".join(parts)


def _relationship_to_dict(r: CharacterRelationship) -> dict:
    """Convert CharacterRelationship model to dict."""
    return {
        "id": r.id,
        "project_id": r.project_id,
        "persona_id_1": r.persona_id_1,
        "persona_id_2": r.persona_id_2,
        "relationship_type": r.relationship_type,
        "description": r.description,
        "intimacy_level": r.intimacy_level,
        "auto_detected": r.auto_detected,
        "detection_confidence": r.detection_confidence,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }

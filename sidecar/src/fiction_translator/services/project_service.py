"""Project CRUD service."""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from fiction_translator.db.models import Chapter, Project

_PROJECT_UPDATABLE = {"name", "description", "source_language", "target_language", "genre", "style_settings", "pipeline_type", "llm_provider"}


def list_projects(db: Session) -> list[dict]:
    """List all projects with chapter counts."""
    # Get chapter counts in one query
    chapter_counts = dict(
        db.query(Chapter.project_id, func.count(Chapter.id))
        .group_by(Chapter.project_id)
        .all()
    )

    projects = db.query(Project).order_by(Project.updated_at.desc()).all()
    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "source_language": p.source_language,
            "target_language": p.target_language,
            "genre": p.genre,
            "pipeline_type": p.pipeline_type,
            "llm_provider": p.llm_provider,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "chapter_count": chapter_counts.get(p.id, 0),
        })
    return result


def create_project(db: Session, name: str, source_language: str = "ko", target_language: str = "en", **kwargs) -> dict:
    """Create a new project."""
    project = Project(
        name=name,
        source_language=source_language,
        target_language=target_language,
        description=kwargs.get("description"),
        genre=kwargs.get("genre"),
        style_settings=kwargs.get("style_settings"),
        pipeline_type=kwargs.get("pipeline_type", "cot_batch"),
        llm_provider=kwargs.get("llm_provider", "gemini"),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_to_dict(project)


def get_project(db: Session, project_id: int) -> dict:
    """Get a single project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project {project_id} not found")
    return _project_to_dict(project)


def update_project(db: Session, project_id: int, **kwargs) -> dict:
    """Update an existing project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project {project_id} not found")
    for key, value in kwargs.items():
        if key in _PROJECT_UPDATABLE:
            setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return _project_to_dict(project)


def delete_project(db: Session, project_id: int) -> dict:
    """Delete a project and all related data (cascades)."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project {project_id} not found")
    db.delete(project)
    db.commit()
    return {"deleted": True, "id": project_id}


def _project_to_dict(p: Project) -> dict:
    """Convert Project model to dict."""
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "source_language": p.source_language,
        "target_language": p.target_language,
        "genre": p.genre,
        "style_settings": p.style_settings,
        "pipeline_type": p.pipeline_type,
        "llm_provider": p.llm_provider,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }

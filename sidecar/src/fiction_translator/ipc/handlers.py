"""JSON-RPC method handlers."""
from __future__ import annotations

import logging
from typing import Any, Callable, Awaitable

from fiction_translator.db.session import get_db

logger = logging.getLogger(__name__)

# Global reference to the server for sending notifications
_server = None

def set_server(server):
    global _server
    _server = server

async def send_progress(stage: str, progress: float, message: str = ""):
    """Send a progress notification to the Tauri host."""
    if _server:
        await _server.send_notification("pipeline.progress", {
            "stage": stage,
            "progress": progress,
            "message": message,
        })


# --- Health ---
async def health_check() -> dict:
    return {"status": "ok", "version": "2.0.0"}


# --- Config ---
_api_keys: dict[str, str] = {}

async def config_set_keys(**keys: str) -> dict:
    """Store API keys in memory (received from Tauri keychain)."""
    _api_keys.update(keys)
    return {"stored": list(keys.keys())}

async def config_get_keys() -> dict:
    """Return which providers have keys configured."""
    return {k: bool(v) for k, v in _api_keys.items()}

async def config_test_provider(provider: str) -> dict:
    """Test if an LLM provider is working."""
    from fiction_translator.llm.providers import get_llm_provider
    try:
        p = get_llm_provider(provider, api_keys=_api_keys)
        response = await p.generate("Say 'hello' in one word.", max_tokens=10)
        return {"success": True, "response": response.text[:100]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Projects ---
async def project_list() -> list[dict]:
    db = get_db()
    try:
        from fiction_translator.services.project_service import list_projects
        return list_projects(db)
    finally:
        db.close()

async def project_create(name: str, source_language: str = "ko", target_language: str = "en", **kwargs) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.project_service import create_project
        return create_project(db, name=name, source_language=source_language, target_language=target_language, **kwargs)
    finally:
        db.close()

async def project_get(project_id: int) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.project_service import get_project
        return get_project(db, project_id)
    finally:
        db.close()

async def project_update(project_id: int, **kwargs) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.project_service import update_project
        return update_project(db, project_id, **kwargs)
    finally:
        db.close()

async def project_delete(project_id: int) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.project_service import delete_project
        return delete_project(db, project_id)
    finally:
        db.close()


# --- Chapters ---
async def chapter_list(project_id: int) -> list[dict]:
    db = get_db()
    try:
        from fiction_translator.services.chapter_service import list_chapters
        return list_chapters(db, project_id)
    finally:
        db.close()

async def chapter_create(project_id: int, title: str, source_content: str = "", **kwargs) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.chapter_service import create_chapter
        return create_chapter(db, project_id=project_id, title=title, source_content=source_content, **kwargs)
    finally:
        db.close()

async def chapter_get(chapter_id: int) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.chapter_service import get_chapter
        return get_chapter(db, chapter_id)
    finally:
        db.close()

async def chapter_update(chapter_id: int, **kwargs) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.chapter_service import update_chapter
        return update_chapter(db, chapter_id, **kwargs)
    finally:
        db.close()

async def chapter_delete(chapter_id: int) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.chapter_service import delete_chapter
        return delete_chapter(db, chapter_id)
    finally:
        db.close()

async def chapter_get_editor_data(chapter_id: int, target_language: str = "en") -> dict:
    db = get_db()
    try:
        from fiction_translator.services.chapter_service import get_editor_data
        return get_editor_data(db, chapter_id, target_language)
    finally:
        db.close()


# --- Glossary ---
async def glossary_list(project_id: int) -> list[dict]:
    db = get_db()
    try:
        from fiction_translator.services.glossary_service import list_glossary
        return list_glossary(db, project_id)
    finally:
        db.close()

async def glossary_create(project_id: int, source_term: str, translated_term: str, **kwargs) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.glossary_service import create_glossary_entry
        return create_glossary_entry(db, project_id=project_id, source_term=source_term, translated_term=translated_term, **kwargs)
    finally:
        db.close()

async def glossary_update(entry_id: int, **kwargs) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.glossary_service import update_glossary_entry
        return update_glossary_entry(db, entry_id, **kwargs)
    finally:
        db.close()

async def glossary_delete(entry_id: int) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.glossary_service import delete_glossary_entry
        return delete_glossary_entry(db, entry_id)
    finally:
        db.close()


# --- Personas ---
async def persona_list(project_id: int) -> list[dict]:
    db = get_db()
    try:
        from fiction_translator.services.persona_service import list_personas
        return list_personas(db, project_id)
    finally:
        db.close()

async def persona_create(project_id: int, name: str, **kwargs) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.persona_service import create_persona
        return create_persona(db, project_id=project_id, name=name, **kwargs)
    finally:
        db.close()

async def persona_update(persona_id: int, **kwargs) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.persona_service import update_persona
        return update_persona(db, persona_id, **kwargs)
    finally:
        db.close()

async def persona_delete(persona_id: int) -> dict:
    db = get_db()
    try:
        from fiction_translator.services.persona_service import delete_persona
        return delete_persona(db, persona_id)
    finally:
        db.close()


# --- Pipeline ---
async def pipeline_translate_chapter(chapter_id: int, target_language: str = "en", **kwargs) -> dict:
    """Start chapter translation pipeline."""
    db = get_db()
    try:
        from fiction_translator.pipeline.graph import run_translation_pipeline
        result = await run_translation_pipeline(
            db=db,
            chapter_id=chapter_id,
            target_language=target_language,
            api_keys=_api_keys,
            progress_callback=send_progress,
            **kwargs,
        )
        return result
    finally:
        db.close()

async def pipeline_cancel() -> dict:
    """Cancel running pipeline."""
    # TODO: implement cancellation
    return {"cancelled": True}


# --- Method Registry ---
def get_all_handlers() -> dict[str, Any]:
    """Return all method name -> handler mappings."""
    return {
        "health.check": health_check,
        "config.set_keys": config_set_keys,
        "config.get_keys": config_get_keys,
        "config.test_provider": config_test_provider,
        "project.list": project_list,
        "project.create": project_create,
        "project.get": project_get,
        "project.update": project_update,
        "project.delete": project_delete,
        "chapter.list": chapter_list,
        "chapter.create": chapter_create,
        "chapter.get": chapter_get,
        "chapter.update": chapter_update,
        "chapter.delete": chapter_delete,
        "chapter.get_editor_data": chapter_get_editor_data,
        "glossary.list": glossary_list,
        "glossary.create": glossary_create,
        "glossary.update": glossary_update,
        "glossary.delete": glossary_delete,
        "persona.list": persona_list,
        "persona.create": persona_create,
        "persona.update": persona_update,
        "persona.delete": persona_delete,
        "pipeline.translate_chapter": pipeline_translate_chapter,
        "pipeline.cancel": pipeline_cancel,
    }

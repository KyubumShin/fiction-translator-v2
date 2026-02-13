"""JSON-RPC method handlers."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from fiction_translator.db.models import Translation, TranslationBatch
from fiction_translator.db.session import get_db
from fiction_translator.services.chapter_service import (
    create_chapter,
    delete_chapter,
    get_chapter,
    get_editor_data,
    list_chapters,
    update_chapter,
)
from fiction_translator.services.export_service import export_chapter_docx, export_chapter_txt
from fiction_translator.services.glossary_service import (
    create_glossary_entry,
    delete_glossary_entry,
    list_glossary,
    update_glossary_entry,
)
from fiction_translator.services.persona_service import (
    create_persona,
    delete_persona,
    list_personas,
    update_persona,
)
from fiction_translator.services.project_service import (
    create_project,
    delete_project,
    get_project,
    list_projects,
    update_project,
)
from fiction_translator.services.segment_service import retranslate_segments

logger = logging.getLogger(__name__)

# Global reference to the server for sending notifications
_server = None

# Global cancellation event
_cancel_event: asyncio.Event | None = None

def _get_cancel_event() -> asyncio.Event:
    global _cancel_event
    if _cancel_event is None:
        _cancel_event = asyncio.Event()
    return _cancel_event

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
class _ApiKeyStore:
    """Thread-safe API key storage."""
    def __init__(self):
        self._keys: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def update(self, keys: dict[str, str]) -> list[str]:
        async with self._lock:
            self._keys.update(keys)
            return list(keys.keys())

    async def get_status(self) -> dict[str, bool]:
        async with self._lock:
            return {k: bool(v) for k, v in self._keys.items()}

    def snapshot(self) -> dict[str, str]:
        """Return a snapshot for passing to pipeline (read-only copy)."""
        return dict(self._keys)

_key_store = _ApiKeyStore()

async def config_set_keys(**keys: str) -> dict:
    """Store API keys in memory (received from Tauri keychain)."""
    stored = await _key_store.update(keys)
    return {"stored": stored}

async def config_get_keys() -> dict:
    """Return which providers have keys configured."""
    return await _key_store.get_status()

async def config_test_provider(provider: str) -> dict:
    """Test if an LLM provider is working."""
    from fiction_translator.llm.providers import get_llm_provider
    try:
        p = get_llm_provider(provider, api_keys=_key_store.snapshot())
        response = await p.generate("Say 'hello' in one word.", max_tokens=10)
        return {"success": True, "response": response.text[:100]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# --- Projects ---
async def project_list() -> list[dict]:
    db = get_db()
    try:
        return list_projects(db)
    finally:
        db.close()

async def project_create(name: str, source_language: str = "ko", target_language: str = "en", **kwargs) -> dict:
    db = get_db()
    try:
        return create_project(db, name=name, source_language=source_language, target_language=target_language, **kwargs)
    finally:
        db.close()

async def project_get(project_id: int) -> dict:
    db = get_db()
    try:
        return get_project(db, project_id)
    finally:
        db.close()

async def project_update(project_id: int, **kwargs) -> dict:
    db = get_db()
    try:
        return update_project(db, project_id, **kwargs)
    finally:
        db.close()

async def project_delete(project_id: int) -> dict:
    db = get_db()
    try:
        return delete_project(db, project_id)
    finally:
        db.close()


# --- Chapters ---
async def chapter_list(project_id: int) -> list[dict]:
    db = get_db()
    try:
        return list_chapters(db, project_id)
    finally:
        db.close()

async def chapter_create(project_id: int, title: str, source_content: str = "", **kwargs) -> dict:
    db = get_db()
    try:
        return create_chapter(db, project_id=project_id, title=title, source_content=source_content, **kwargs)
    finally:
        db.close()

async def chapter_get(chapter_id: int) -> dict:
    db = get_db()
    try:
        return get_chapter(db, chapter_id)
    finally:
        db.close()

async def chapter_update(chapter_id: int, **kwargs) -> dict:
    db = get_db()
    try:
        return update_chapter(db, chapter_id, **kwargs)
    finally:
        db.close()

async def chapter_delete(chapter_id: int) -> dict:
    db = get_db()
    try:
        return delete_chapter(db, chapter_id)
    finally:
        db.close()

async def chapter_get_editor_data(chapter_id: int, target_language: str = "en") -> dict:
    db = get_db()
    try:
        return get_editor_data(db, chapter_id, target_language)
    finally:
        db.close()


# --- Glossary ---
async def glossary_list(project_id: int) -> list[dict]:
    db = get_db()
    try:
        return list_glossary(db, project_id)
    finally:
        db.close()

async def glossary_create(project_id: int, source_term: str, translated_term: str, **kwargs) -> dict:
    db = get_db()
    try:
        return create_glossary_entry(db, project_id=project_id, source_term=source_term, translated_term=translated_term, **kwargs)
    finally:
        db.close()

async def glossary_update(entry_id: int, **kwargs) -> dict:
    db = get_db()
    try:
        return update_glossary_entry(db, entry_id, **kwargs)
    finally:
        db.close()

async def glossary_delete(entry_id: int) -> dict:
    db = get_db()
    try:
        return delete_glossary_entry(db, entry_id)
    finally:
        db.close()


# --- Personas ---
async def persona_list(project_id: int) -> list[dict]:
    db = get_db()
    try:
        return list_personas(db, project_id)
    finally:
        db.close()

async def persona_create(project_id: int, name: str, **kwargs) -> dict:
    db = get_db()
    try:
        return create_persona(db, project_id=project_id, name=name, **kwargs)
    finally:
        db.close()

async def persona_update(persona_id: int, **kwargs) -> dict:
    db = get_db()
    try:
        return update_persona(db, persona_id, **kwargs)
    finally:
        db.close()

async def persona_delete(persona_id: int) -> dict:
    db = get_db()
    try:
        return delete_persona(db, persona_id)
    finally:
        db.close()


# --- Pipeline ---
async def pipeline_translate_chapter(chapter_id: int, target_language: str = "en", use_cot: bool = True, **kwargs) -> dict:
    """Start chapter translation pipeline."""
    # Clear any previous cancellation
    event = _get_cancel_event()
    event.clear()

    db = get_db()
    try:
        from fiction_translator.pipeline.graph import run_translation_pipeline
        result = await run_translation_pipeline(
            db=db,
            chapter_id=chapter_id,
            target_language=target_language,
            api_keys=_key_store.snapshot(),
            progress_callback=send_progress,
            use_cot=use_cot,
            cancel_event=event,
            **kwargs,
        )
        return result
    finally:
        db.close()

async def pipeline_cancel() -> dict:
    """Cancel running pipeline."""
    event = _get_cancel_event()
    event.set()
    return {"cancelled": True}


# --- Export ---
async def export_chapter_txt_handler(chapter_id: int, target_language: str = "en") -> dict:
    db = get_db()
    try:
        return export_chapter_txt(db, chapter_id, target_language)
    finally:
        db.close()

async def export_chapter_docx_handler(chapter_id: int, target_language: str = "en") -> dict:
    db = get_db()
    try:
        return export_chapter_docx(db, chapter_id, target_language)
    finally:
        db.close()


# --- Segments ---
async def segment_update_translation(segment_id: int, translated_text: str, target_language: str = "en") -> dict:
    """Update a segment's translation text."""
    db = get_db()
    try:
        translation = db.query(Translation).filter(
            Translation.segment_id == segment_id,
            Translation.target_language == target_language,
        ).first()
        if not translation:
            raise ValueError(f"Translation not found for segment {segment_id}")
        translation.translated_text = translated_text
        translation.manually_edited = True
        db.commit()
        return {"updated": True, "segment_id": segment_id}
    finally:
        db.close()


# --- Segment Re-translate ---
async def segment_retranslate(segment_ids: list[int], target_language: str = "en", user_guide: str = "") -> dict:
    """Re-translate specific segments with user guidance."""
    db = get_db()
    try:
        return await retranslate_segments(
            db=db,
            segment_ids=segment_ids,
            target_language=target_language,
            user_guide=user_guide,
            api_keys=_key_store.snapshot(),
        )
    finally:
        db.close()


# --- Batch Reasoning ---
async def batch_get_reasoning(batch_id: int) -> dict:
    """Get CoT reasoning data for a translation batch."""
    db = get_db()
    try:
        batch = db.query(TranslationBatch).filter(TranslationBatch.id == batch_id).first()
        if not batch:
            return {"found": False}
        return {
            "found": True,
            "id": batch.id,
            "situation_summary": batch.situation_summary,
            "character_events": batch.character_events,
            "full_cot_json": batch.full_cot_json,
            "segment_ids": batch.segment_ids,
            "review_feedback": batch.review_feedback,
            "review_iteration": batch.review_iteration,
        }
    finally:
        db.close()


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
        "segment.update_translation": segment_update_translation,
        "segment.retranslate": segment_retranslate,
        "batch.get_reasoning": batch_get_reasoning,
        "export.chapter_txt": export_chapter_txt_handler,
        "export.chapter_docx": export_chapter_docx_handler,
    }

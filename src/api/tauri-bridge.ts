import { invoke } from "@tauri-apps/api/core";
import { listen, type UnlistenFn } from "@tauri-apps/api/event";
import type { PipelineProgress } from "./types";

/**
 * Call a JSON-RPC method on the Python sidecar via Tauri.
 */
export async function rpc<T = unknown>(
  method: string,
  params?: Record<string, unknown>
): Promise<T> {
  const result = await invoke<T>("rpc_call", { method, params: params ?? {} });
  return result;
}

/**
 * Listen for pipeline progress events from the sidecar.
 */
export function onPipelineProgress(
  callback: (progress: PipelineProgress) => void
): Promise<UnlistenFn> {
  return listen<PipelineProgress>("pipeline:progress", (event) => {
    callback(event.payload);
  });
}

/**
 * Listen for sidecar status events.
 */
export function onSidecarStatus(
  callback: (status: { connected: boolean; error?: string }) => void
): Promise<UnlistenFn> {
  return listen("sidecar:status", (event) => {
    callback(event.payload as { connected: boolean; error?: string });
  });
}

// Convenience methods
export const api = {
  // Health
  healthCheck: () => rpc<{ status: string; version: string }>("health.check"),

  // Config
  setApiKeys: (keys: Record<string, string>) => rpc("config.set_keys", keys),
  getApiKeys: () => rpc<Record<string, boolean>>("config.get_keys"),
  testProvider: (provider: string) => rpc<{ success: boolean; error?: string }>("config.test_provider", { provider }),

  // Projects
  listProjects: () => rpc<Record<string, unknown>[]>("project.list"),
  createProject: (data: { name: string; source_language?: string; target_language?: string; genre?: string; description?: string }) =>
    rpc("project.create", data),
  getProject: (projectId: number) => rpc("project.get", { project_id: projectId }),
  updateProject: (projectId: number, data: Record<string, unknown>) =>
    rpc("project.update", { project_id: projectId, ...data }),
  deleteProject: (projectId: number) => rpc("project.delete", { project_id: projectId }),

  // Chapters
  listChapters: (projectId: number) => rpc("chapter.list", { project_id: projectId }),
  createChapter: (data: { project_id: number; title: string; source_content?: string }) =>
    rpc("chapter.create", data),
  getChapter: (chapterId: number) => rpc("chapter.get", { chapter_id: chapterId }),
  updateChapter: (chapterId: number, data: Record<string, unknown>) =>
    rpc("chapter.update", { chapter_id: chapterId, ...data }),
  deleteChapter: (chapterId: number) => rpc("chapter.delete", { chapter_id: chapterId }),
  getEditorData: (chapterId: number, targetLanguage: string = "en") =>
    rpc("chapter.get_editor_data", { chapter_id: chapterId, target_language: targetLanguage }),

  // Glossary
  listGlossary: (projectId: number) => rpc("glossary.list", { project_id: projectId }),
  createGlossaryEntry: (data: { project_id: number; source_term: string; translated_term: string; term_type?: string; notes?: string }) =>
    rpc("glossary.create", data),
  updateGlossaryEntry: (entryId: number, data: Record<string, unknown>) =>
    rpc("glossary.update", { entry_id: entryId, ...data }),
  deleteGlossaryEntry: (entryId: number) => rpc("glossary.delete", { entry_id: entryId }),

  // Personas
  listPersonas: (projectId: number) => rpc("persona.list", { project_id: projectId }),
  createPersona: (data: { project_id: number; name: string; [key: string]: unknown }) =>
    rpc("persona.create", data),
  updatePersona: (personaId: number, data: Record<string, unknown>) =>
    rpc("persona.update", { persona_id: personaId, ...data }),
  deletePersona: (personaId: number) => rpc("persona.delete", { persona_id: personaId }),

  // Pipeline
  translateChapter: (chapterId: number, targetLanguage: string = "en", useCot: boolean = true) =>
    rpc("pipeline.translate_chapter", { chapter_id: chapterId, target_language: targetLanguage, use_cot: useCot }),
  cancelPipeline: () => rpc("pipeline.cancel"),

  // Segments
  updateSegmentTranslation: (segmentId: number, translatedText: string, targetLanguage: string = "en") =>
    rpc("segment.update_translation", { segment_id: segmentId, translated_text: translatedText, target_language: targetLanguage }),

  // Segment re-translate
  retranslateSegments: (segmentIds: number[], targetLanguage: string, userGuide: string) =>
    rpc("segment.retranslate", { segment_ids: segmentIds, target_language: targetLanguage, user_guide: userGuide }),

  // Export
  exportChapterTxt: (chapterId: number, targetLanguage: string = "en") =>
    rpc<{ path: string; format: string; size: number }>("export.chapter_txt", { chapter_id: chapterId, target_language: targetLanguage }),
  exportChapterDocx: (chapterId: number, targetLanguage: string = "en") =>
    rpc<{ path: string; format: string }>("export.chapter_docx", { chapter_id: chapterId, target_language: targetLanguage }),

  // Batch reasoning
  getBatchReasoning: (batchId: number) =>
    rpc<{ found: boolean; situation_summary?: string; character_events?: Record<string, unknown>; full_cot_json?: Record<string, unknown>; review_feedback?: Record<string, unknown> }>("batch.get_reasoning", { batch_id: batchId }),
};

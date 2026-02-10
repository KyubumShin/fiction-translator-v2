// JSON-RPC 2.0 types
export interface JsonRpcRequest {
  jsonrpc: "2.0";
  method: string;
  params?: Record<string, unknown> | unknown[];
  id?: number | string;
}

export interface JsonRpcResponse<T = unknown> {
  jsonrpc: "2.0";
  id: number | string | null;
  result?: T;
  error?: JsonRpcError;
}

export interface JsonRpcError {
  code: number;
  message: string;
  data?: unknown;
}

// Domain types
export interface Project {
  id: number;
  name: string;
  description: string | null;
  source_language: string;
  target_language: string;
  genre: string | null;
  pipeline_type: string;
  llm_provider: string;
  created_at: string;
  updated_at: string;
  chapter_count?: number;
}

export interface Chapter {
  id: number;
  project_id: number;
  title: string;
  order: number;
  source_content: string | null;
  translated_content: string | null;
  translation_stale: boolean;
  created_at: string;
  updated_at: string;
  segment_count?: number;
  translated_count?: number;
}

export interface Segment {
  id: number;
  chapter_id: number;
  order: number;
  source_text: string;
  speaker: string | null;
  segment_type: string;
  source_start_offset: number | null;
  source_end_offset: number | null;
}

export interface Translation {
  id: number;
  segment_id: number;
  target_language: string;
  translated_text: string;
  status: TranslationStatus;
  manually_edited: boolean;
  translated_start_offset: number | null;
  translated_end_offset: number | null;
  batch_id: number | null;
}

export type TranslationStatus = "pending" | "translating" | "translated" | "reviewed" | "approved";

export interface GlossaryEntry {
  id: number;
  project_id: number;
  source_term: string;
  translated_term: string;
  term_type: string;
  notes: string | null;
  context: string | null;
  auto_detected: boolean;
}

export interface Persona {
  id: number;
  project_id: number;
  name: string;
  aliases: string[] | null;
  personality: string | null;
  speech_style: string | null;
  formality_level: number;
  age_group: string | null;
  appearance_count: number;
  auto_detected: boolean;
}

export interface PersonaSuggestion {
  id: number;
  persona_id: number;
  field_name: string;
  suggested_value: string;
  confidence: number;
  status: "pending" | "approved" | "rejected";
}

export interface EditorData {
  source_connected_text: string;
  translated_connected_text: string;
  segment_map: SegmentMapEntry[];
}

export interface SegmentMapEntry {
  segment_id: number;
  source_start: number;
  source_end: number;
  translated_start: number;
  translated_end: number;
  type: string;
  speaker: string | null;
  batch_id: number | null;
}

export interface PipelineProgress {
  stage: string;
  progress: number;
  message: string;
}

export interface PipelineRun {
  id: number;
  chapter_id: number;
  target_language: string;
  status: "pending" | "running" | "completed" | "failed" | "cancelled";
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  stats: Record<string, unknown> | null;
}

export const LANGUAGES = {
  ko: "Korean",
  ja: "Japanese",
  zh: "Chinese",
  en: "English",
  es: "Spanish",
  fr: "French",
  de: "German",
  pt: "Portuguese",
  ru: "Russian",
  vi: "Vietnamese",
  th: "Thai",
  id: "Indonesian",
} as const;

export type LanguageCode = keyof typeof LANGUAGES;

export const LLM_PROVIDERS = {
  gemini: { name: "Google Gemini", model: "gemini-2.0-flash" },
  claude: { name: "Anthropic Claude", model: "claude-sonnet-4-5-20250929" },
  openai: { name: "OpenAI GPT", model: "gpt-4o" },
} as const;

export const GENRE_OPTIONS = [
  "fantasy", "romance", "thriller", "litrpg", "horror",
  "comedy", "sci-fi", "mystery", "drama", "action",
] as const;

export const PIPELINE_STAGES = [
  { key: "load_context", label: "Loading Context" },
  { key: "segmentation", label: "Segmentation" },
  { key: "character_extraction", label: "Character Extraction" },
  { key: "validation", label: "Validation" },
  { key: "translation", label: "Translation" },
  { key: "review", label: "Review" },
  { key: "persona_learning", label: "Persona Learning" },
  { key: "finalize", label: "Finalizing" },
] as const;

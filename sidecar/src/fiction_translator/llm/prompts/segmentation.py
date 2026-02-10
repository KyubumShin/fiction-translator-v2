"""Text segmentation prompt template.

Asks the LLM to split source text into typed segments (narrative, dialogue,
action, thought) with speaker attribution for dialogue lines.
"""
from __future__ import annotations


def build_segmentation_prompt(source_text: str, source_language: str) -> str:
    """Build a segmentation prompt for the LLM.

    Parameters
    ----------
    source_text : str
        The raw chapter text to segment.
    source_language : str
        ISO language code (ko, ja, zh, en, ...).

    Returns
    -------
    str
        The full prompt string that expects a JSON response.
    """
    lang_names = {
        "ko": "Korean",
        "ja": "Japanese",
        "zh": "Chinese",
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
    }
    lang_label = lang_names.get(source_language, source_language)

    return f"""You are a literary text segmentation expert for {lang_label} fiction.

Analyze the following text and split it into logical translation segments.
Each segment should be one of:
- "narrative": narration, description, exposition
- "dialogue": a character speaking (include the dialogue markers)
- "action": physical actions or movements
- "thought": internal thoughts or monologue

For dialogue segments, identify the speaker if possible.

Rules:
1. Preserve paragraph boundaries as segment boundaries.
2. Keep dialogue lines as individual segments when possible.
3. Never split a sentence across segments.
4. Keep related narration together (do not over-segment).
5. Each segment must be non-empty.

Return ONLY valid JSON in this format:
{{
  "segments": [
    {{
      "text": "the segment text exactly as it appears",
      "type": "narrative|dialogue|action|thought",
      "speaker": "character name or null"
    }}
  ]
}}

TEXT TO SEGMENT:
---
{source_text}
---

Return ONLY the JSON object, no explanation."""

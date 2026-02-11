"""Character extraction prompt template.

Asks the LLM to identify characters appearing in a set of text segments,
with details about their role and speaking patterns.
"""
from __future__ import annotations


def build_character_extraction_prompt(
    segments_text: str,
    source_language: str,
    existing_personas: list[dict] | None = None,
) -> str:
    """Build a character-extraction prompt.

    Parameters
    ----------
    segments_text : str
        Concatenated segment texts to analyse.
    source_language : str
        ISO language code.
    existing_personas : list[dict] | None
        Already-known personas from the project DB.

    Returns
    -------
    str
        Prompt expecting a JSON response.
    """
    lang_names = {
        "ko": "Korean", "ja": "Japanese", "zh": "Chinese", "en": "English",
    }
    lang_label = lang_names.get(source_language, source_language)

    existing_section = ""
    if existing_personas:
        names = [p.get("name", "?") for p in existing_personas]
        existing_section = (
            "\nAlready-known characters in this project: "
            + ", ".join(names) + "\n"
            "If you detect any of these characters, use the EXACT same name.\n"
        )

    return f"""You are a literary character analyst for {lang_label} fiction.

Analyse the following text segments and identify every character that appears.
{existing_section}
For each character provide:
- name: the character's name as it appears in the text
- aliases: other names / titles / nicknames used for the same character
- role: protagonist | antagonist | supporting | minor | mentioned
- speaking_lines: approximate count of dialogue lines in the text
- personality_hints: brief personality notes from context clues
- speech_style_hints: any notable speech patterns or register

Write personality_hints and speech_style_hints in {lang_label}.

Return ONLY valid JSON:
{{
  "characters": [
    {{
      "name": "string",
      "aliases": ["string"],
      "role": "protagonist|antagonist|supporting|minor|mentioned",
      "speaking_lines": 0,
      "personality_hints": "string or null",
      "speech_style_hints": "string or null"
    }}
  ]
}}

TEXT:
---
{segments_text}
---

Return ONLY the JSON object."""

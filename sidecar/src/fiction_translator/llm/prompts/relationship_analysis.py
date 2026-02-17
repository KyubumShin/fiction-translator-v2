"""Relationship analysis prompt template.

Asks the LLM to identify character relationships from translated text.
"""
from __future__ import annotations


def build_relationship_analysis_prompt(
    translated_text: str,
    detected_characters: list[dict],
    existing_personas: list[dict],
    existing_relationships: list[dict],
    target_language: str = "en",
    source_language: str = "ko",
) -> str:
    """Build a relationship-analysis prompt.

    Parameters
    ----------
    translated_text : str
        The translated chapter text.
    detected_characters : list[dict]
        Characters detected in the current chapter.
    existing_personas : list[dict]
        Known personas from the project.
    existing_relationships : list[dict]
        Already-known relationships.
    target_language : str
        The translation target language.
    source_language : str
        The source language.

    Returns
    -------
    str
        Prompt expecting JSON response.
    """
    lang_names = {
        "ko": "Korean", "ja": "Japanese", "zh": "Chinese", "en": "English",
    }
    lang_label = lang_names.get(source_language, source_language)

    char_names = [c.get("name", "?") for c in detected_characters]
    char_list = ", ".join(char_names) if char_names else "(none detected)"

    existing_section = ""
    if existing_relationships:
        parts = []
        for r in existing_relationships:
            p1_name = _find_name(r.get("persona_id_1"), existing_personas)
            p2_name = _find_name(r.get("persona_id_2"), existing_personas)
            rel_type = r.get("relationship_type", "unknown")
            intimacy = r.get("intimacy_level", 5)
            parts.append(f"  - {p1_name} <-> {p2_name}: {rel_type} (intimacy: {intimacy}/10)")
        existing_section = (
            "\n## Existing relationships\n" + "\n".join(parts) + "\n"
        )

    personas_section = ""
    if existing_personas:
        parts = []
        for p in existing_personas:
            line = f"  - {p['name']} (id: {p['id']})"
            if p.get("personality"):
                line += f" | {p['personality'][:60]}"
            parts.append(line)
        personas_section = (
            "\n## Known characters\n" + "\n".join(parts) + "\n"
        )

    return f"""You are a literary relationship analyst. Analyse the translated text below and
identify relationships between characters.

Characters detected in this chapter: {char_list}
{personas_section}{existing_section}
For each pair of characters that interact in the text, identify:
- The nature of their relationship (type)
- Intimacy/closeness level (1=distant strangers, 10=inseparable)
- Brief description of their dynamic
- Confidence score (0.0-1.0)

Relationship types: friend, rival, family, romantic, mentor, subordinate, enemy, ally, acquaintance

Focus on relationships VISIBLE in this text passage. Update existing relationships if new
evidence changes the dynamic. Write descriptions in {lang_label} (the source language).

Return ONLY valid JSON:
{{
  "relationship_updates": [
    {{
      "character_1": "name of first character",
      "character_2": "name of second character",
      "relationship_type": "friend|rival|family|romantic|mentor|subordinate|enemy|ally|acquaintance",
      "intimacy_level": 7,
      "description": "brief description of their relationship dynamic",
      "confidence": 0.8,
      "evidence": "brief quote or reference from the text"
    }}
  ]
}}

TRANSLATED TEXT:
---
{translated_text[:8000]}
---

Return ONLY the JSON object."""


def _find_name(persona_id: int | None, personas: list[dict]) -> str:
    """Find persona name by ID."""
    if persona_id is None:
        return "Unknown"
    for p in personas:
        if p.get("id") == persona_id:
            return p.get("name", "Unknown")
    return "Unknown"

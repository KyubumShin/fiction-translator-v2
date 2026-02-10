"""Persona analysis prompt template.

Asks the LLM to extract character insights from translated text to update
the persona database.
"""
from __future__ import annotations


def build_persona_analysis_prompt(
    translated_text: str,
    detected_characters: list[dict],
    existing_personas: list[dict] | None = None,
    target_language: str = "en",
) -> str:
    """Build a persona-analysis prompt.

    Parameters
    ----------
    translated_text : str
        The translated chapter text.
    detected_characters : list[dict]
        Characters detected in the current chapter.
    existing_personas : list[dict] | None
        Known personas from the project.
    target_language : str
        The translation target language.

    Returns
    -------
    str
        Prompt expecting JSON response.
    """
    char_names = [c.get("name", "?") for c in detected_characters]
    char_list = ", ".join(char_names) if char_names else "(none detected)"

    existing_section = ""
    if existing_personas:
        parts = []
        for p in existing_personas:
            line = f"  - {p['name']}"
            if p.get("speech_style"):
                line += f" | style: {p['speech_style']}"
            if p.get("personality"):
                line += f" | personality: {p['personality']}"
            parts.append(line)
        existing_section = (
            "\n## Existing persona records\n" + "\n".join(parts) + "\n"
        )

    return f"""You are a literary character analyst. Analyse the translated text below and
extract insights about each character's voice and personality.

Characters detected in this chapter: {char_list}
{existing_section}
For each character that speaks in the text, provide:
- personality observations (new or reinforced)
- speech style notes (formality, vocabulary, quirks)
- suggested formality_level (1=very casual ... 5=very formal)
- any new aliases discovered
- confidence score (0.0-1.0)

Focus on NEW information not already captured in existing persona records.

Return ONLY valid JSON:
{{
  "persona_updates": [
    {{
      "name": "character name",
      "field": "personality|speech_style|formality_level|aliases",
      "value": "the suggested update",
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


def build_persona_learning_prompt(
    translated_text: str,
    existing_personas: list[dict],
) -> str:
    """
    Build prompt for learning new character traits from translations.

    Analyzes translated text to extract insights that can enhance
    existing character personas or identify new characters.

    Args:
        translated_text: Translated text to analyze
        existing_personas: List of existing persona dicts with 'name', 'traits' fields

    Returns:
        Prompt string requesting persona learning
    """
    parts = [
        "Analyze this translated fiction text to learn about character voices and personalities.",
        "",
        "## Translated Text",
        translated_text[:8000],
        "",
    ]

    if existing_personas:
        parts.extend([
            "## Known Characters",
            "",
            "These character personas already exist:",
            "",
        ])
        for persona in existing_personas:
            name = persona.get("name", "Unknown")
            parts.append(f"### {name}")
            if persona.get("speech_style"):
                parts.append(f"- **Speech Style**: {persona['speech_style']}")
            if persona.get("personality"):
                parts.append(f"- **Personality**: {persona['personality']}")
            if persona.get("formality_level"):
                parts.append(f"- **Formality Level**: {persona['formality_level']}")
            parts.append("")

        parts.append("Focus on NEW insights or traits not already captured.")
        parts.append("")

    parts.extend([
        "## Analysis Goals",
        "",
        "For each character who appears in this text:",
        "",
        "1. **Speech Patterns**: How do they speak? Any verbal tics or quirks?",
        "2. **Formality**: Rate formality level (1=very casual, 5=very formal)",
        "3. **Personality**: What traits are revealed through dialogue/actions?",
        "4. **Relationships**: How do they interact with other characters?",
        "5. **Character Arc**: Any development or changes in this passage?",
        "",
        "## Response Format",
        "",
        "Respond with JSON:",
        "```json",
        "{",
        '  "character_insights": [',
        '    {',
        '      "name": "Character Name",',
        '      "new_traits": {',
        '        "speech_pattern": "Uses lots of technical jargon, speaks in short sentences",',
        '        "formality_level": 2,',
        '        "personality": "Analytical, impatient, protective of friends",',
        '        "verbal_tics": "Often says \\"obviously\\" when explaining things"',
        '      },',
        '      "relationships": [',
        '        {',
        '          "with_character": "Other Character",',
        '          "dynamic": "Mentor-student, somewhat condescending but caring"',
        '        }',
        '      ],',
        '      "confidence": 0.85,',
        '      "evidence": "Quote or description from text supporting this insight"',
        '    }',
        '  ],',
        '  "new_characters": [',
        '    {',
        '      "name": "New Character Name",',
        '      "first_appearance": true,',
        '      "initial_traits": {',
        '        "speech_pattern": "...",',
        '        "formality_level": 3,',
        '        "personality": "..."',
        '      },',
        '      "role": "supporting",',
        '      "confidence": 0.7',
        '    }',
        '  ],',
        '  "narrative_insights": {',
        '    "genre_markers": ["Action", "Mystery"],',
        '    "tone": "Tense with moments of dark humor",',
        '    "pacing": "Fast-paced with quick dialogue exchanges"',
        '  }',
        "}",
        "```",
        "",
        "**Important Guidelines**:",
        "",
        "- Only include insights with confidence > 0.7",
        "- Provide specific evidence (quotes or descriptions) for each insight",
        "- Focus on actionable traits that improve future translations",
        "- Distinguish between character personality and narrator voice",
        "- Note any changes in character voice compared to existing personas",
        "",
        "**Formality Levels**:",
        "1. Very casual (slang, contractions, informal)",
        "2. Casual (conversational, some contractions)",
        "3. Neutral (standard, professional)",
        "4. Formal (polite, minimal contractions)",
        "5. Very formal (honorifics, elaborate speech)",
    ])

    return "\n".join(parts)

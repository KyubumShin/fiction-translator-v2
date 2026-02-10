"""Translation review prompt template.

Asks the LLM to evaluate translation quality and flag segments that need
re-translation.
"""
from __future__ import annotations


def build_review_prompt(
    pairs: list[dict],
    source_language: str,
    target_language: str,
    glossary: dict[str, str] | None = None,
    personas_context: str = "",
) -> str:
    """Build a review prompt.

    Parameters
    ----------
    pairs : list[dict]
        Each dict has: segment_id, source_text, translated_text, type, speaker.
    source_language, target_language : str
        ISO language codes.
    glossary : dict | None
        Glossary to verify adherence.
    personas_context : str
        Character voice guide.

    Returns
    -------
    str
        Prompt expecting JSON response.
    """
    lang_names = {
        "ko": "Korean", "ja": "Japanese", "zh": "Chinese", "en": "English",
    }
    src_label = lang_names.get(source_language, source_language)
    tgt_label = lang_names.get(target_language, target_language)

    glossary_section = ""
    if glossary:
        entries = "\n".join(f"  {k} -> {v}" for k, v in glossary.items())
        glossary_section = f"""
## Glossary to verify
{entries}
"""

    persona_section = ""
    if personas_context:
        persona_section = f"""
{personas_context}
"""

    pair_lines = []
    for p in pairs:
        speaker_tag = f" [speaker: {p.get('speaker', '')}]" if p.get("speaker") else ""
        pair_lines.append(
            f"[{p['segment_id']}|{p.get('type', 'narrative')}{speaker_tag}]\n"
            f"  SRC: {p['source_text']}\n"
            f"  TGT: {p['translated_text']}"
        )
    pairs_block = "\n\n".join(pair_lines)

    return f"""You are a senior translation reviewer for {src_label} to {tgt_label} literary translation.

Review the following source/translation pairs for quality.
{glossary_section}{persona_section}
## Evaluation criteria
1. **Accuracy**: Does the translation faithfully convey the meaning?
2. **Glossary adherence**: Are glossary terms used correctly?
3. **Character voice**: Does dialogue match the character's personality and register?
4. **Natural flow**: Does the {tgt_label} read naturally as prose?
5. **Consistency**: Are names, terms, and tone consistent across segments?

For each segment, decide PASS or FLAG. Only flag segments with genuine issues.

Return ONLY valid JSON:
{{
  "overall_passed": true|false,
  "summary": "Brief overall assessment",
  "segment_reviews": [
    {{
      "segment_id": 1,
      "verdict": "pass|flag",
      "issue": "description of issue or null",
      "suggestion": "how to fix or null"
    }}
  ]
}}

TRANSLATION PAIRS:
---
{pairs_block}
---

Return ONLY the JSON object."""

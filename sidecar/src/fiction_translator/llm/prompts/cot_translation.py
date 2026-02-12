"""Chain-of-thought translation prompt template.

The CoT approach asks the LLM to first analyse the scene context, then
translate each segment while maintaining consistency with the glossary and
character voices.
"""
from __future__ import annotations


def build_cot_translation_prompt(
    segments: list[dict],
    source_language: str,
    target_language: str,
    glossary: dict[str, str] | None = None,
    personas_context: str = "",
    style_context: str = "",
    review_feedback: list[dict] | None = None,
    user_guide: str = "",
) -> str:
    """Build a CoT batch-translation prompt.

    Parameters
    ----------
    segments : list[dict]
        Each dict has keys: id (int), text (str), type (str), speaker (str|None).
    source_language, target_language : str
        ISO language codes.
    glossary : dict
        source_term -> translated_term mapping.
    personas_context : str
        Formatted character voice guide.
    style_context : str
        Project-level style preferences.
    review_feedback : list[dict] | None
        Feedback from a previous review iteration to incorporate.
    user_guide : str
        User-provided instructions to guide this specific translation.

    Returns
    -------
    str
        Full prompt expecting JSON response.
    """
    lang_names = {
        "ko": "Korean", "ja": "Japanese", "zh": "Chinese", "en": "English",
        "es": "Spanish", "fr": "French", "de": "German",
    }
    src_label = lang_names.get(source_language, source_language)
    tgt_label = lang_names.get(target_language, target_language)

    # ── Glossary section ─────────────────────────────────────────────
    glossary_section = ""
    if glossary:
        entries = "\n".join(f"  {k} -> {v}" for k, v in glossary.items())
        glossary_section = f"""
## Glossary Reference (terms pre-applied in source text — verify correct usage)
{entries}
"""

    # ── Personas section ─────────────────────────────────────────────
    personas_section = ""
    if personas_context:
        personas_section = f"""
{personas_context}
"""

    # ── Style section ────────────────────────────────────────────────
    style_section = ""
    if style_context:
        style_section = f"""
## Style Guidelines
{style_context}
"""

    # ── User guide section ─────────────────────────────────────────
    user_guide_section = ""
    if user_guide:
        user_guide_section = f"""
## User Translation Guide
{user_guide}
"""

    # ── Review feedback section ──────────────────────────────────────
    feedback_section = ""
    if review_feedback:
        items = []
        for fb in review_feedback:
            sid = fb.get("segment_id", "?")
            issue = fb.get("issue", "")
            suggestion = fb.get("suggestion", "")
            items.append(f"  - Segment {sid}: {issue}. Suggestion: {suggestion}")
        feedback_section = """
## Reviewer Feedback (address these issues in your translation)
""" + "\n".join(items) + "\n"

    # ── Segments to translate ────────────────────────────────────────
    seg_lines = []
    for seg in segments:
        speaker_tag = f" [speaker: {seg['speaker']}]" if seg.get("speaker") else ""
        seg_lines.append(
            f"[{seg['id']}|{seg['type']}{speaker_tag}] {seg['text']}"
        )
    segments_block = "\n".join(seg_lines)

    return f"""You are an expert literary translator from {src_label} to {tgt_label}.

Translate the following numbered segments using Chain-of-Thought reasoning.
{glossary_section}{personas_section}{style_section}{user_guide_section}{feedback_section}
## Instructions
1. First, write a brief SITUATION SUMMARY describing the scene context.
2. Then list CHARACTER EVENTS -- what each character does or feels in this passage.
3. Identify any UNKNOWN TERMS -- source-language words that are proper nouns, special terminology, skills, items, place names, or organization names that should be added to a glossary for consistency.
4. Finally, provide the TRANSLATION for each segment.

Rules:
- Preserve the literary tone and style of the original.
- Maintain consistent character voices as described in the persona guide.
- Use glossary terms EXACTLY as specified.
- For dialogue, capture the speaker's personality and register.
- Do NOT add or remove content; translate faithfully.
- Preserve paragraph breaks within segments.

Return ONLY valid JSON in this exact format:
{{
  "situation_summary": "Brief scene description",
  "character_events": [
    {{"character": "name", "event": "what they do/feel"}}
  ],
  "unknown_terms": [
    {{"source_term": "original word", "translated_term": "translated word", "term_type": "name|place|item|skill|organization|general"}}
  ],
  "translations": [
    {{"segment_id": 1, "text": "translated text"}}
  ]
}}

SEGMENTS TO TRANSLATE:
---
{segments_block}
---

Return ONLY the JSON object."""


def build_simple_translation_prompt(
    segments: list[dict],
    source_language: str,
    target_language: str,
    glossary: dict[str, str] | None = None,
    personas_context: str = "",
    style_context: str = "",
    review_feedback: list[dict] | None = None,
    user_guide: str = "",
) -> str:
    """Build a direct translation prompt WITHOUT Chain-of-Thought reasoning.

    Skips situation_summary, character_events, and unknown_terms analysis.
    Still uses glossary and persona context for consistency.
    """
    lang_names = {
        "ko": "Korean", "ja": "Japanese", "zh": "Chinese", "en": "English",
        "es": "Spanish", "fr": "French", "de": "German",
    }
    src_label = lang_names.get(source_language, source_language)
    tgt_label = lang_names.get(target_language, target_language)

    # ── Glossary section
    glossary_section = ""
    if glossary:
        entries = "\n".join(f"  {k} -> {v}" for k, v in glossary.items())
        glossary_section = f"""
## Glossary Reference (terms pre-applied in source text — verify correct usage)
{entries}
"""

    # ── Personas section
    personas_section = ""
    if personas_context:
        personas_section = f"""
{personas_context}
"""

    # ── Style section
    style_section = ""
    if style_context:
        style_section = f"""
## Style Guidelines
{style_context}
"""

    # ── User guide section
    user_guide_section = ""
    if user_guide:
        user_guide_section = f"""
## User Translation Guide
{user_guide}
"""

    # ── Review feedback section
    feedback_section = ""
    if review_feedback:
        items = []
        for fb in review_feedback:
            sid = fb.get("segment_id", "?")
            issue = fb.get("issue", "")
            suggestion = fb.get("suggestion", "")
            items.append(f"  - Segment {sid}: {issue}. Suggestion: {suggestion}")
        feedback_section = """
## Reviewer Feedback (address these issues in your translation)
""" + "\n".join(items) + "\n"

    # ── Segments to translate
    seg_lines = []
    for seg in segments:
        speaker_tag = f" [speaker: {seg['speaker']}]" if seg.get("speaker") else ""
        seg_lines.append(
            f"[{seg['id']}|{seg['type']}{speaker_tag}] {seg['text']}"
        )
    segments_block = "\n".join(seg_lines)

    return f"""You are an expert literary translator from {src_label} to {tgt_label}.

Translate the following numbered segments directly.
{glossary_section}{personas_section}{style_section}{user_guide_section}{feedback_section}
## Instructions
- Preserve the literary tone and style of the original.
- Maintain consistent character voices as described in the persona guide.
- Use glossary terms EXACTLY as specified.
- For dialogue, capture the speaker's personality and register.
- Do NOT add or remove content; translate faithfully.
- Preserve paragraph breaks within segments.

Return ONLY valid JSON in this exact format:
{{
  "translations": [
    {{"segment_id": 1, "text": "translated text"}}
  ]
}}

SEGMENTS TO TRANSLATE:
---
{segments_block}
---

Return ONLY the JSON object."""

"""Translation validation prompt template.

Reserved for future LLM-assisted validation of segmentation quality.
Currently validation is done via deterministic rules in the validator node.
"""
from __future__ import annotations


def build_validation_prompt(
    segments: list[dict],
    source_text: str,
    source_language: str,
) -> str:
    """Build a validation prompt for LLM-assisted segmentation review.

    Currently unused -- the validator node uses deterministic checks.
    This is provided for future enhancement where an LLM can verify
    that segments form a coherent, complete partition of the source text.
    """
    seg_summary = "\n".join(
        f"  [{s.get('order', i)}] type={s.get('type', '?')} len={len(s.get('text', ''))} "
        f"speaker={s.get('speaker', 'none')}"
        for i, s in enumerate(segments)
    )

    return f"""Review the following segmentation of a {source_language} text.

Source text length: {len(source_text)} characters
Number of segments: {len(segments)}

Segment summary:
{seg_summary}

Check:
1. Do segments cover the entire source text without gaps?
2. Are segment types correctly classified?
3. Are dialogue speakers correctly identified?

Return JSON:
{{
  "valid": true|false,
  "issues": ["list of issues found"]
}}"""

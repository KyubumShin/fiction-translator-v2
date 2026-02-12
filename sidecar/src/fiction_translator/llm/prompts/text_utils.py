"""Text utilities for prompt preparation."""
from __future__ import annotations

import re


def normalize_quotes(text: str) -> str:
    """Replace smart/curly quotes with straight ASCII equivalents.

    Only normalizes Western smart quotes. CJK corner brackets
    (\u300C, \u300D) are preserved as they serve structural roles
    in East Asian text.
    """
    replacements = {
        '\u201C': '"',  # left double
        '\u201D': '"',  # right double
        '\u2018': "'",  # left single
        '\u2019': "'",  # right single
    }
    for smart, straight in replacements.items():
        text = text.replace(smart, straight)
    return text


def build_glossary_pattern(glossary: dict[str, str]) -> re.Pattern | None:
    """Compile a regex that matches any glossary source term.

    Terms are sorted longest-first so that longer terms match before
    their substrings (e.g. "검은 별" matches before "검은").

    Returns ``None`` when *glossary* is empty.
    """
    if not glossary:
        return None
    sorted_terms = sorted(glossary.keys(), key=len, reverse=True)
    pattern_str = "|".join(re.escape(t) for t in sorted_terms)
    return re.compile(pattern_str)


def apply_glossary_exchange(
    text: str,
    glossary: dict[str, str],
    pattern: re.Pattern | None = None,
) -> str:
    """Replace glossary source terms in *text* with their translations.

    If *pattern* is provided it is reused; otherwise one is compiled
    on the fly.  Pass a pre-compiled pattern when processing many
    segments with the same glossary.
    """
    if not glossary or not text:
        return text
    if pattern is None:
        pattern = build_glossary_pattern(glossary)
    if pattern is None:
        return text
    return pattern.sub(lambda m: glossary[m.group(0)], text)


def filter_glossary_for_batch(
    glossary: dict[str, str],
    batch_texts: list[str],
) -> dict[str, str]:
    """Return the subset of *glossary* whose source terms appear in *batch_texts*.

    Used to trim the prompt glossary section down to only relevant
    entries, reducing token usage.
    """
    if not glossary or not batch_texts:
        return {}
    combined = " ".join(batch_texts)
    return {k: v for k, v in glossary.items() if k in combined}

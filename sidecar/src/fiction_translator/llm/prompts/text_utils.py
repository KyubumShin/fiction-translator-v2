"""Text utilities for prompt preparation."""
from __future__ import annotations


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

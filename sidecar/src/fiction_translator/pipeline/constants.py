"""Shared constants for the translation pipeline."""
from __future__ import annotations

import re

# ── Language-specific dialogue markers ────────────────────────────────
DIALOGUE_MARKERS: dict[str, list[re.Pattern]] = {
    "ko": [
        re.compile(r'^["\u201C].*["\u201D]\s*$'),        # "..." full line
        re.compile(r'^["\u201C]'),                        # starts with "
        re.compile(r'^\u300C.*\u300D'),                   # Korean angular quotes
    ],
    "ja": [
        re.compile(r'^\u300C.*\u300D'),                   # Japanese brackets
        re.compile(r'^\u300E.*\u300F'),                   # double brackets
        re.compile(r'^["\u201C].*["\u201D]'),
    ],
    "zh": [
        re.compile(r'^\u201C.*\u201D'),                   # Chinese quotes
        re.compile(r'^["\u300C]'),
    ],
    "en": [
        re.compile(r'^["\u201C].*["\u201D]\s*$'),
        re.compile(r'^["\u201C]'),
        re.compile(r"^'.*'\s*$"),
    ],
}

# Speaker attribution patterns per language
SPEAKER_PATTERNS: dict[str, list[re.Pattern]] = {
    "ko": [
        re.compile(r'["\u201D]\s*(?:\ub77c\uace0|\uc774\ub77c\uace0)\s+(\w+)'),
        re.compile(r'(\w+)[\uc774\uac00\uc740\ub294]\s+\ub9d0\ud588\ub2e4'),
        re.compile(r'(\w+)\s*:\s*["\u201C]'),
    ],
    "ja": [
        re.compile(r'\u300D\u3068(\w+)'),
        re.compile(r'(\w+)\u306F\u8A00\u3063\u305F'),
    ],
    "zh": [
        re.compile(r'\u201D(\w+)\u8BF4'),
        re.compile(r'(\w+)\u8BF4\s*[:\uFF1A]\s*\u201C'),
    ],
    "en": [
        re.compile(r'["\u201D]\s+said\s+(\w+)', re.IGNORECASE),
        re.compile(r'(\w+)\s+said[,.]?\s*["\u201C]', re.IGNORECASE),
        re.compile(r'(\w+)\s*:\s*["\u201C]'),
    ],
}

"""Tests for text_utils module."""
import pytest
from fiction_translator.llm.prompts.text_utils import normalize_quotes


class TestNormalizeQuotes:
    def test_left_double_quote(self):
        assert normalize_quotes('\u201CHello') == '"Hello'

    def test_right_double_quote(self):
        assert normalize_quotes('Hello\u201D') == 'Hello"'

    def test_left_single_quote(self):
        assert normalize_quotes('\u2018Hello') == "'Hello"

    def test_right_single_quote(self):
        assert normalize_quotes('Hello\u2019') == "Hello'"

    def test_mixed_smart_and_straight(self):
        assert normalize_quotes('\u201CHello\u201D and "world"') == '"Hello" and "world"'

    def test_no_quotes(self):
        text = "Hello world, no quotes here."
        assert normalize_quotes(text) == text

    def test_empty_string(self):
        assert normalize_quotes("") == ""

    def test_cjk_brackets_preserved(self):
        text = '\u300C\u3053\u3093\u306B\u3061\u306F\u300D'
        assert normalize_quotes(text) == text

    def test_korean_with_smart_quotes(self):
        text = '\u201C\uac80\uc740 \ubcc4\uc774 \ub5a8\uc5b4\uc9c0\ub294 \ub0a0\u201D'
        expected = '"\uac80\uc740 \ubcc4\uc774 \ub5a8\uc5b4\uc9c0\ub294 \ub0a0"'
        assert normalize_quotes(text) == expected

    def test_all_four_types(self):
        text = '\u201CHe said, \u2018hello\u2019\u201D'
        expected = '"He said, \'hello\'"'
        assert normalize_quotes(text) == expected

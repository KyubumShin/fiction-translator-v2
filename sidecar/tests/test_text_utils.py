"""Tests for text_utils module."""
import pytest
from fiction_translator.llm.prompts.text_utils import (
    normalize_quotes,
    build_glossary_pattern,
    apply_glossary_exchange,
    filter_glossary_for_batch,
)


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


class TestBuildGlossaryPattern:
    def test_empty_glossary(self):
        assert build_glossary_pattern({}) is None

    def test_single_term(self):
        pat = build_glossary_pattern({"검은": "Black"})
        assert pat is not None
        assert pat.search("검은 별이 떨어지는 날")

    def test_longest_first_ordering(self):
        glossary = {"검": "Sword", "검은 별": "Black Star"}
        pat = build_glossary_pattern(glossary)
        # "검은 별" should match as a whole, not "검" first
        m = pat.search("검은 별이 떨어지는 날")
        assert m.group(0) == "검은 별"

    def test_regex_metachar_escaping(self):
        glossary = {"이름(가명)": "Name (alias)", "가격+세금": "price+tax"}
        pat = build_glossary_pattern(glossary)
        assert pat.search("이름(가명)을 사용했다")
        assert pat.search("가격+세금은 얼마인가")
        # Should NOT match without the metachar
        assert not pat.search("이름가명을 사용했다")


class TestApplyGlossaryExchange:
    def test_simple_replacement(self):
        glossary = {"마법사": "Wizard"}
        result = apply_glossary_exchange("그 마법사가 왔다", glossary)
        assert result == "그 Wizard가 왔다"

    def test_longest_match_first(self):
        glossary = {"검": "Sword", "검은 별": "Black Star"}
        result = apply_glossary_exchange("검은 별이 빛났다", glossary)
        assert result == "Black Star이 빛났다"

    def test_no_match(self):
        glossary = {"마법사": "Wizard"}
        text = "전사가 싸웠다"
        assert apply_glossary_exchange(text, glossary) == text

    def test_empty_glossary(self):
        assert apply_glossary_exchange("hello", {}) == "hello"

    def test_empty_text(self):
        assert apply_glossary_exchange("", {"a": "b"}) == ""

    def test_multiple_occurrences(self):
        glossary = {"용": "Dragon"}
        result = apply_glossary_exchange("용이 용을 물었다", glossary)
        assert result == "Dragon이 Dragon을 물었다"

    def test_adjacent_cjk_terms(self):
        glossary = {"흑": "Black", "마법": "Magic"}
        result = apply_glossary_exchange("흑마법을 썼다", glossary)
        # Both should be replaced independently
        assert "Black" in result
        assert "Magic" in result

    def test_precompiled_pattern_reuse(self):
        glossary = {"마법사": "Wizard", "전사": "Warrior"}
        pat = build_glossary_pattern(glossary)
        r1 = apply_glossary_exchange("마법사가 왔다", glossary, pat)
        r2 = apply_glossary_exchange("전사가 싸웠다", glossary, pat)
        assert r1 == "Wizard가 왔다"
        assert r2 == "Warrior가 싸웠다"


class TestFilterGlossaryForBatch:
    def test_filters_correctly(self):
        glossary = {"마법사": "Wizard", "전사": "Warrior", "도적": "Thief"}
        batch = ["마법사가 왔다", "전사가 싸웠다"]
        result = filter_glossary_for_batch(glossary, batch)
        assert result == {"마법사": "Wizard", "전사": "Warrior"}

    def test_empty_glossary(self):
        assert filter_glossary_for_batch({}, ["some text"]) == {}

    def test_empty_batch(self):
        assert filter_glossary_for_batch({"a": "b"}, []) == {}

    def test_all_present(self):
        glossary = {"용": "Dragon", "검": "Sword"}
        batch = ["용이 검을 들었다"]
        result = filter_glossary_for_batch(glossary, batch)
        assert result == glossary

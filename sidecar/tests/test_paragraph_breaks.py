"""Tests for paragraph break preservation through the pipeline."""
import re
import pytest

from fiction_translator.pipeline.nodes.segmenter import _split_paragraphs, _rule_based_segment


class TestSplitParagraphs:
    def test_single_paragraph(self):
        result = _split_paragraphs("Hello world")
        assert len(result) == 1
        text, offset, has_break = result[0]
        assert text == "Hello world"
        assert offset == 0
        assert has_break is False

    def test_two_paragraphs(self):
        result = _split_paragraphs("First paragraph\n\nSecond paragraph")
        assert len(result) == 2
        text1, offset1, break1 = result[0]
        text2, offset2, break2 = result[1]
        assert text1 == "First paragraph"
        assert break1 is False
        assert text2 == "Second paragraph"
        assert break2 is True

    def test_single_newline_no_break(self):
        result = _split_paragraphs("Line one\nLine two")
        assert len(result) == 1
        text, offset, has_break = result[0]
        assert "Line one\nLine two" == text
        assert has_break is False

    def test_multiple_paragraphs(self):
        text = "Para 1\n\nPara 2\n\nPara 3"
        result = _split_paragraphs(text)
        assert len(result) == 3
        assert result[0][2] is False  # first never has break
        assert result[1][2] is True
        assert result[2][2] is True

    def test_whitespace_gap(self):
        result = _split_paragraphs("Para 1\n  \n  \nPara 2")
        assert len(result) == 2
        assert result[1][2] is True


class TestRuleBasedSegment:
    def test_preserves_has_preceding_break(self):
        text = "First paragraph.\n\nSecond paragraph."
        segments = _rule_based_segment(text, "en")
        assert len(segments) == 2
        assert segments[0].get("has_preceding_break") is False
        assert segments[1].get("has_preceding_break") is True

    def test_no_break_for_single_paragraph(self):
        text = "Just one paragraph here."
        segments = _rule_based_segment(text, "en")
        assert len(segments) == 1
        assert segments[0].get("has_preceding_break") is False


class TestOffsetAccuracy:
    """Verify that offset arithmetic is correct by slicing connected text."""

    def test_source_offsets_with_paragraph_breaks(self):
        """Simulate what get_editor_data does and verify offsets."""
        seg1_text = "First paragraph."
        seg2_text = "Second paragraph."
        has_break_list = [False, True]

        # Build connected text
        parts = []
        offset = 0
        starts = []
        ends = []

        for i, text in enumerate([seg1_text, seg2_text]):
            if i > 0:
                sep = "\n\n" if has_break_list[i] else "\n"
                parts.append(sep)
                offset += len(sep)

            starts.append(offset)
            ends.append(offset + len(text))
            parts.append(text)
            offset = ends[-1]

        connected = "".join(parts)

        # Verify slicing
        assert connected[starts[0]:ends[0]] == seg1_text
        assert connected[starts[1]:ends[1]] == seg2_text
        assert "\n\n" in connected[ends[0]:starts[1]]

    def test_source_offsets_without_breaks(self):
        """All segments use single newline."""
        seg1_text = "First."
        seg2_text = "Second."
        has_break_list = [False, False]

        parts = []
        offset = 0
        starts = []
        ends = []

        for i, text in enumerate([seg1_text, seg2_text]):
            if i > 0:
                sep = "\n\n" if has_break_list[i] else "\n"
                parts.append(sep)
                offset += len(sep)

            starts.append(offset)
            ends.append(offset + len(text))
            parts.append(text)
            offset = ends[-1]

        connected = "".join(parts)

        assert connected[starts[0]:ends[0]] == seg1_text
        assert connected[starts[1]:ends[1]] == seg2_text
        assert connected[ends[0]:starts[1]] == "\n"

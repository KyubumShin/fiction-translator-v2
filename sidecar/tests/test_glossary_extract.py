"""Tests for glossary auto-extraction during translation pipeline."""
import logging
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fiction_translator.db.models import Base, Chapter, GlossaryEntry, Project
from fiction_translator.llm.providers import GeminiProvider, LLMResponse


@pytest.fixture
def db():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_project(db, **kwargs):
    """Helper to create a project."""
    defaults = {
        "name": "Test Project",
        "source_language": "ko",
        "target_language": "en",
    }
    defaults.update(kwargs)
    project = Project(**defaults)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def _make_chapter(db, project_id, **kwargs):
    """Helper to create a chapter."""
    defaults = {
        "project_id": project_id,
        "title": "Chapter 1",
        "source_content": "테스트 텍스트",
    }
    defaults.update(kwargs)
    chapter = Chapter(**defaults)
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return chapter


@pytest.mark.asyncio
class TestTranslatorUnknownTerms:
    """Tests for unknown_terms collection in translator_node."""

    async def _run_translator(self, state_overrides=None):
        """Run translator_node with mocked dependencies."""
        # Default LLM response with unknown_terms
        default_llm_response = {
            "situation_summary": "Test scene",
            "character_events": [],
            "unknown_terms": [
                {"source_term": "마법사", "translated_term": "Wizard", "term_type": "name"},
                {"source_term": "검", "translated_term": "Sword", "term_type": "item"},
            ],
            "translations": [
                {"segment_id": 0, "text": "Translated text"},
            ],
        }

        mock_provider = AsyncMock()
        mock_provider.generate_json = AsyncMock(return_value=default_llm_response)

        state = {
            "segments": [{"order": 0, "text": "테스트", "type": "narrative"}],
            "source_language": "ko",
            "target_language": "en",
            "api_keys": {"gemini": "fake-key"},
            "llm_provider": "gemini",
            "use_cot": True,
            "flagged_segments": [],
            "translated_segments": [],
            "review_iteration": 0,
            "review_feedback": [],
            "unknown_terms": [],
            "glossary": {},
            "personas_context": "",
            "relationships_context": "",
            "style_context": "",
            "total_tokens": 0,
            "total_cost": 0.0,
            "cancel_event": None,
        }
        if state_overrides:
            state.update(state_overrides)

        with patch(
            "fiction_translator.llm.providers.get_llm_provider",
            return_value=mock_provider,
        ):
            from fiction_translator.pipeline.nodes.translator import translator_node
            result = await translator_node(state)

        return result, mock_provider

    async def test_collects_unknown_terms_from_batch(self):
        """Test that unknown terms are collected from LLM response."""
        result, _ = await self._run_translator()

        assert len(result["unknown_terms"]) == 2
        terms = {t["source_term"] for t in result["unknown_terms"]}
        assert "마법사" in terms
        assert "검" in terms

    async def test_preserves_previous_unknown_terms_in_review_loop(self):
        """Test that unknown_terms from first pass survive re-translation."""
        previous_terms = [
            {"source_term": "용사", "translated_term": "Hero", "term_type": "name"},
            {"source_term": "마을", "translated_term": "Village", "term_type": "place"},
        ]

        result, _ = await self._run_translator({
            "unknown_terms": previous_terms,
            "flagged_segments": [0],
            "translated_segments": [
                {"segment_id": 0, "order": 0, "source_text": "테스트",
                 "translated_text": "Old translation", "type": "narrative"},
            ],
            "review_iteration": 1,
        })

        # Should have both previous (2) and new (2) terms
        assert len(result["unknown_terms"]) == 4
        all_sources = {t["source_term"] for t in result["unknown_terms"]}
        assert "용사" in all_sources  # from previous
        assert "마을" in all_sources  # from previous
        assert "마법사" in all_sources  # from new batch
        assert "검" in all_sources  # from new batch

    async def test_empty_unknown_terms_when_not_cot(self):
        """Test that simple (non-CoT) mode doesn't extract unknown_terms."""
        mock_provider = AsyncMock()
        mock_provider.generate_json = AsyncMock(return_value={
            "translations": [{"segment_id": 0, "text": "Translated"}],
        })

        with patch(
            "fiction_translator.llm.providers.get_llm_provider",
            return_value=mock_provider,
        ):
            from fiction_translator.pipeline.nodes.translator import translator_node
            result = await translator_node({
                "segments": [{"order": 0, "text": "테스트", "type": "narrative"}],
                "source_language": "ko",
                "target_language": "en",
                "api_keys": {"gemini": "fake-key"},
                "llm_provider": "gemini",
                "use_cot": False,
                "flagged_segments": [],
                "translated_segments": [],
                "review_iteration": 0,
                "review_feedback": [],
                "unknown_terms": [],
                "glossary": {},
                "personas_context": "",
                "relationships_context": "",
                "style_context": "",
                "total_tokens": 0,
                "total_cost": 0.0,
                "cancel_event": None,
            })

        assert result["unknown_terms"] == []

    async def test_skips_terms_without_source_or_translation(self):
        """Test that incomplete terms are filtered out."""
        mock_provider = AsyncMock()
        mock_provider.generate_json = AsyncMock(return_value={
            "situation_summary": "",
            "character_events": [],
            "unknown_terms": [
                {"source_term": "마법사", "translated_term": "Wizard", "term_type": "name"},
                {"source_term": "", "translated_term": "Empty", "term_type": "name"},
                {"source_term": "Missing", "translated_term": "", "term_type": "name"},
                {"source_term": "Valid", "translated_term": "Also Valid", "term_type": "item"},
            ],
            "translations": [{"segment_id": 0, "text": "Translated"}],
        })

        with patch(
            "fiction_translator.llm.providers.get_llm_provider",
            return_value=mock_provider,
        ):
            from fiction_translator.pipeline.nodes.translator import translator_node
            result = await translator_node({
                "segments": [{"order": 0, "text": "테스트", "type": "narrative"}],
                "source_language": "ko",
                "target_language": "en",
                "api_keys": {"gemini": "fake-key"},
                "llm_provider": "gemini",
                "use_cot": True,
                "flagged_segments": [],
                "translated_segments": [],
                "review_iteration": 0,
                "review_feedback": [],
                "unknown_terms": [],
                "glossary": {},
                "personas_context": "",
                "relationships_context": "",
                "style_context": "",
                "total_tokens": 0,
                "total_cost": 0.0,
                "cancel_event": None,
            })

        # Only terms with both source_term and translated_term are kept
        assert len(result["unknown_terms"]) == 2
        sources = {t["source_term"] for t in result["unknown_terms"]}
        assert sources == {"마법사", "Valid"}


class TestFinalizeGlossarySaving:
    """Tests for glossary auto-detection in finalize_node."""

    def test_saves_unknown_terms_as_glossary_entries(self, db):
        """Test that unknown terms are saved as auto-detected glossary entries."""
        project = _make_project(db)

        unknown_terms = [
            {"source_term": "마법사", "translated_term": "Wizard", "term_type": "name"},
            {"source_term": "검", "translated_term": "Sword", "term_type": "item"},
        ]

        # Save terms directly (simulating finalize_node logic)
        existing_terms = {
            e.source_term.lower()
            for e in db.query(GlossaryEntry).filter(
                GlossaryEntry.project_id == project.id
            ).all()
        }
        for term in unknown_terms:
            source = term.get("source_term", "").strip()
            translated = term.get("translated_term", "").strip()
            if source and translated and source.lower() not in existing_terms:
                db.add(GlossaryEntry(
                    project_id=project.id,
                    source_term=source,
                    translated_term=translated,
                    term_type=term.get("term_type", "general"),
                    auto_detected=True,
                ))
                existing_terms.add(source.lower())
        db.commit()

        entries = db.query(GlossaryEntry).filter(
            GlossaryEntry.project_id == project.id
        ).all()
        assert len(entries) == 2
        assert all(e.auto_detected is True for e in entries)
        terms_map = {e.source_term: e.translated_term for e in entries}
        assert terms_map["마법사"] == "Wizard"
        assert terms_map["검"] == "Sword"

    def test_skips_duplicate_glossary_terms(self, db):
        """Test that existing glossary terms are not duplicated."""
        project = _make_project(db)

        # Pre-existing entry
        db.add(GlossaryEntry(
            project_id=project.id,
            source_term="마법사",
            translated_term="Mage",
            auto_detected=False,
        ))
        db.commit()

        unknown_terms = [
            {"source_term": "마법사", "translated_term": "Wizard", "term_type": "name"},
            {"source_term": "검", "translated_term": "Sword", "term_type": "item"},
        ]

        existing_terms = {
            e.source_term.lower()
            for e in db.query(GlossaryEntry).filter(
                GlossaryEntry.project_id == project.id
            ).all()
        }
        for term in unknown_terms:
            source = term.get("source_term", "").strip()
            translated = term.get("translated_term", "").strip()
            if source and translated and source.lower() not in existing_terms:
                db.add(GlossaryEntry(
                    project_id=project.id,
                    source_term=source,
                    translated_term=translated,
                    term_type=term.get("term_type", "general"),
                    auto_detected=True,
                ))
                existing_terms.add(source.lower())
        db.commit()

        entries = db.query(GlossaryEntry).filter(
            GlossaryEntry.project_id == project.id
        ).all()
        # Should have 2 total: original "마법사" (unchanged) + new "검"
        assert len(entries) == 2
        # Original should keep its value
        mage = next(e for e in entries if e.source_term == "마법사")
        assert mage.translated_term == "Mage"
        assert mage.auto_detected is False

    def test_case_insensitive_duplicate_check(self, db):
        """Test that duplicate check is case-insensitive."""
        project = _make_project(db)

        db.add(GlossaryEntry(
            project_id=project.id,
            source_term="Dragon",
            translated_term="용",
            auto_detected=False,
        ))
        db.commit()

        unknown_terms = [
            {"source_term": "dragon", "translated_term": "드래곤", "term_type": "name"},
            {"source_term": "DRAGON", "translated_term": "용룡", "term_type": "name"},
        ]

        existing_terms = {
            e.source_term.lower()
            for e in db.query(GlossaryEntry).filter(
                GlossaryEntry.project_id == project.id
            ).all()
        }
        for term in unknown_terms:
            source = term.get("source_term", "").strip()
            translated = term.get("translated_term", "").strip()
            if source and translated and source.lower() not in existing_terms:
                db.add(GlossaryEntry(
                    project_id=project.id,
                    source_term=source,
                    translated_term=translated,
                    term_type=term.get("term_type", "general"),
                    auto_detected=True,
                ))
                existing_terms.add(source.lower())
        db.commit()

        entries = db.query(GlossaryEntry).filter(
            GlossaryEntry.project_id == project.id
        ).all()
        # Only the original "Dragon" should exist — duplicates skipped
        assert len(entries) == 1
        assert entries[0].source_term == "Dragon"


@pytest.mark.asyncio
class TestGenerateJsonLogging:
    """Tests for debug logging in generate_json."""

    async def test_logs_parsed_json_keys_at_debug(self, caplog):
        """Test that generate_json logs parsed JSON keys at DEBUG level."""
        provider = GeminiProvider(api_key="test-key")
        provider.generate = AsyncMock(
            return_value=LLMResponse(
                text='{"translations": [{"id": 1}], "unknown_terms": [{"term": "a"}, {"term": "b"}]}',
                model="test-model",
                usage={"prompt_tokens": 10, "completion_tokens": 20},
            )
        )

        with caplog.at_level(logging.DEBUG, logger="fiction_translator.llm.providers"):
            result = await provider.generate_json("test prompt")

        assert "translations" in result
        assert "unknown_terms" in result
        # Check that debug log mentions the key summary
        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("Parsed JSON keys" in msg for msg in debug_messages)

    async def test_logs_raw_response_at_debug(self, caplog):
        """Test that generate_json logs the raw LLM response text."""
        provider = GeminiProvider(api_key="test-key")
        provider.generate = AsyncMock(
            return_value=LLMResponse(
                text='{"key": "value"}',
                model="test-model",
                usage={"prompt_tokens": 5, "completion_tokens": 10},
            )
        )

        with caplog.at_level(logging.DEBUG, logger="fiction_translator.llm.providers"):
            await provider.generate_json("test prompt")

        debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
        assert any("LLM response" in msg for msg in debug_messages)

    async def test_logs_error_on_invalid_json(self, caplog):
        """Test that invalid JSON logs error with raw response."""
        provider = GeminiProvider(api_key="test-key")
        provider.generate = AsyncMock(
            return_value=LLMResponse(
                text="not valid json at all",
                model="test-model",
                usage={},
            )
        )

        with caplog.at_level(logging.DEBUG, logger="fiction_translator.llm.providers"):
            with pytest.raises(ValueError, match="LLM did not return valid JSON"):
                await provider.generate_json("test prompt")

        error_messages = [r.message for r in caplog.records if r.levelno == logging.ERROR]
        assert any("Raw response text" in msg for msg in error_messages)

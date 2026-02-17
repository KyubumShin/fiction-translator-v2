"""Tests for IPC handler registration."""
import pytest

from fiction_translator.ipc.handlers import (
    _ApiKeyStore,
    get_all_handlers,
    health_check,
)


@pytest.mark.asyncio
class TestHealthCheck:
    """Tests for health_check handler."""

    async def test_returns_correct_structure(self):
        """Test that health_check returns the expected structure."""
        result = await health_check()
        assert "status" in result
        assert "version" in result
        assert result["status"] == "ok"
        assert result["version"] == "2.0.0"


class TestGetAllHandlers:
    """Tests for get_all_handlers method registry."""

    def test_returns_dict(self):
        """Test that get_all_handlers returns a dictionary."""
        handlers = get_all_handlers()
        assert isinstance(handlers, dict)

    def test_contains_health_check(self):
        """Test that health.check is registered."""
        handlers = get_all_handlers()
        assert "health.check" in handlers
        assert handlers["health.check"] == health_check

    def test_contains_config_methods(self):
        """Test that config methods are registered."""
        handlers = get_all_handlers()
        expected_config = ["config.set_keys", "config.get_keys", "config.test_provider"]
        for method in expected_config:
            assert method in handlers

    def test_contains_project_methods(self):
        """Test that project methods are registered."""
        handlers = get_all_handlers()
        expected_project = [
            "project.list",
            "project.create",
            "project.get",
            "project.update",
            "project.delete",
        ]
        for method in expected_project:
            assert method in handlers

    def test_contains_chapter_methods(self):
        """Test that chapter methods are registered."""
        handlers = get_all_handlers()
        expected_chapter = [
            "chapter.list",
            "chapter.create",
            "chapter.get",
            "chapter.update",
            "chapter.delete",
            "chapter.get_editor_data",
        ]
        for method in expected_chapter:
            assert method in handlers

    def test_contains_glossary_methods(self):
        """Test that glossary methods are registered."""
        handlers = get_all_handlers()
        expected_glossary = [
            "glossary.list",
            "glossary.create",
            "glossary.update",
            "glossary.delete",
        ]
        for method in expected_glossary:
            assert method in handlers

    def test_contains_persona_methods(self):
        """Test that persona methods are registered."""
        handlers = get_all_handlers()
        expected_persona = [
            "persona.list",
            "persona.create",
            "persona.update",
            "persona.delete",
        ]
        for method in expected_persona:
            assert method in handlers

    def test_contains_pipeline_methods(self):
        """Test that pipeline methods are registered."""
        handlers = get_all_handlers()
        expected_pipeline = [
            "pipeline.translate_chapter",
            "pipeline.cancel",
        ]
        for method in expected_pipeline:
            assert method in handlers

    def test_contains_segment_methods(self):
        """Test that segment methods are registered."""
        handlers = get_all_handlers()
        expected_segment = [
            "segment.update_translation",
            "segment.retranslate",
        ]
        for method in expected_segment:
            assert method in handlers

    def test_contains_batch_methods(self):
        """Test that batch methods are registered."""
        handlers = get_all_handlers()
        assert "batch.get_reasoning" in handlers

    def test_contains_export_methods(self):
        """Test that export methods are registered."""
        handlers = get_all_handlers()
        expected_export = [
            "export.chapter_txt",
            "export.chapter_docx",
        ]
        for method in expected_export:
            assert method in handlers

    def test_all_handlers_are_callable(self):
        """Test that all registered handlers are callable."""
        handlers = get_all_handlers()
        for name, handler in handlers.items():
            assert callable(handler), f"Handler {name} is not callable"

    def test_handler_count(self):
        """Test that the expected number of handlers are registered."""
        handlers = get_all_handlers()
        # Count expected handlers:
        # health: 1
        # config: 3
        # project: 5
        # chapter: 6
        # glossary: 4
        # persona: 4
        # relationship: 4
        # pipeline: 2
        # segment: 2
        # batch: 1
        # export: 2
        # Total: 34
        assert len(handlers) == 34


@pytest.mark.asyncio
class TestApiKeyStore:
    """Tests for _ApiKeyStore class."""

    async def test_update_adds_keys(self):
        """Test that update method adds keys."""
        store = _ApiKeyStore()
        stored = await store.update({"gemini": "key1", "claude": "key2"})

        assert "gemini" in stored
        assert "claude" in stored
        assert len(stored) == 2

    async def test_update_returns_stored_key_names(self):
        """Test that update returns list of stored key names."""
        store = _ApiKeyStore()
        stored = await store.update({"gemini": "key1"})

        assert stored == ["gemini"]

    async def test_update_merges_keys(self):
        """Test that update merges new keys with existing ones."""
        store = _ApiKeyStore()
        await store.update({"gemini": "key1"})
        await store.update({"claude": "key2"})

        status = await store.get_status()
        assert "gemini" in status
        assert "claude" in status

    async def test_update_overwrites_existing_keys(self):
        """Test that update overwrites existing key values."""
        store = _ApiKeyStore()
        await store.update({"gemini": "old-key"})
        await store.update({"gemini": "new-key"})

        snapshot = store.snapshot()
        assert snapshot["gemini"] == "new-key"

    async def test_get_status_returns_bool_dict(self):
        """Test that get_status returns dict with boolean values."""
        store = _ApiKeyStore()
        await store.update({"gemini": "key1", "claude": ""})

        status = await store.get_status()
        assert status["gemini"] is True
        assert status["claude"] is False

    async def test_get_status_empty_string_is_false(self):
        """Test that empty string keys return False in status."""
        store = _ApiKeyStore()
        await store.update({"gemini": ""})

        status = await store.get_status()
        assert status["gemini"] is False

    async def test_snapshot_returns_dict_copy(self):
        """Test that snapshot returns a copy of keys."""
        store = _ApiKeyStore()
        await store.update({"gemini": "key1", "claude": "key2"})

        snapshot = store.snapshot()
        assert snapshot == {"gemini": "key1", "claude": "key2"}

    async def test_snapshot_is_readonly_copy(self):
        """Test that modifying snapshot doesn't affect store."""
        store = _ApiKeyStore()
        await store.update({"gemini": "key1"})

        snapshot = store.snapshot()
        snapshot["gemini"] = "modified"

        snapshot2 = store.snapshot()
        assert snapshot2["gemini"] == "key1"  # Original unchanged

    async def test_concurrent_updates_are_thread_safe(self):
        """Test that concurrent updates use locking correctly."""
        store = _ApiKeyStore()

        async def update_task(key, value):
            await store.update({key: value})

        # Run multiple updates concurrently
        import asyncio
        await asyncio.gather(
            update_task("key1", "value1"),
            update_task("key2", "value2"),
            update_task("key3", "value3"),
        )

        status = await store.get_status()
        assert len(status) == 3
        assert status["key1"] is True
        assert status["key2"] is True
        assert status["key3"] is True

    async def test_empty_store_snapshot(self):
        """Test that snapshot of empty store returns empty dict."""
        store = _ApiKeyStore()
        snapshot = store.snapshot()
        assert snapshot == {}

    async def test_empty_store_status(self):
        """Test that status of empty store returns empty dict."""
        store = _ApiKeyStore()
        status = await store.get_status()
        assert status == {}

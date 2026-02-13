"""Tests for pipeline callback utilities."""
import asyncio

import pytest

from fiction_translator.pipeline.callbacks import (
    PIPELINE_STAGES,
    PipelineCancelled,
    check_cancelled,
    notify,
    stage_progress,
)


class TestStageProgress:
    """Tests for stage_progress function."""

    def test_load_context_stage(self):
        progress = stage_progress("load_context")
        assert progress == 1 / 8  # First of 8 stages
        assert progress == 0.125

    def test_segmentation_stage(self):
        progress = stage_progress("segmentation")
        assert progress == 2 / 8
        assert progress == 0.25

    def test_character_extraction_stage(self):
        progress = stage_progress("character_extraction")
        assert progress == 3 / 8
        assert progress == 0.375

    def test_validation_stage(self):
        progress = stage_progress("validation")
        assert progress == 4 / 8
        assert progress == 0.5

    def test_translation_stage(self):
        progress = stage_progress("translation")
        assert progress == 5 / 8
        assert progress == 0.625

    def test_review_stage(self):
        progress = stage_progress("review")
        assert progress == 6 / 8
        assert progress == 0.75

    def test_persona_learning_stage(self):
        progress = stage_progress("persona_learning")
        assert progress == 7 / 8
        assert progress == 0.875

    def test_finalize_stage(self):
        progress = stage_progress("finalize")
        assert progress == 8 / 8
        assert progress == 1.0

    def test_unknown_stage_returns_zero(self):
        progress = stage_progress("unknown_stage")
        assert progress == 0.0

    def test_empty_string_returns_zero(self):
        progress = stage_progress("")
        assert progress == 0.0

    def test_all_stages_present(self):
        """Verify all expected stages are in PIPELINE_STAGES."""
        expected = [
            "load_context",
            "segmentation",
            "character_extraction",
            "validation",
            "translation",
            "review",
            "persona_learning",
            "finalize",
        ]
        assert PIPELINE_STAGES == expected


@pytest.mark.asyncio
class TestCheckCancelled:
    """Tests for check_cancelled function."""

    async def test_not_cancelled_when_event_not_set(self):
        """Should not raise when event is not set."""
        event = asyncio.Event()
        state = {"cancel_event": event}

        # Should not raise
        await check_cancelled(state)

    async def test_raises_when_event_is_set(self):
        """Should raise PipelineCancelled when event is set."""
        event = asyncio.Event()
        event.set()
        state = {"cancel_event": event}

        with pytest.raises(PipelineCancelled, match="Pipeline cancelled by user"):
            await check_cancelled(state)

    async def test_no_error_when_event_is_none(self):
        """Should not raise when cancel_event is None."""
        state = {"cancel_event": None}

        # Should not raise
        await check_cancelled(state)

    async def test_no_error_when_event_not_in_state(self):
        """Should not raise when cancel_event key is missing."""
        state = {}

        # Should not raise
        await check_cancelled(state)

    async def test_multiple_checks(self):
        """Test checking multiple times with same event."""
        event = asyncio.Event()
        state = {"cancel_event": event}

        # Should not raise
        await check_cancelled(state)
        await check_cancelled(state)

        # Set the event
        event.set()

        # Should raise on subsequent checks
        with pytest.raises(PipelineCancelled):
            await check_cancelled(state)

        with pytest.raises(PipelineCancelled):
            await check_cancelled(state)


@pytest.mark.asyncio
class TestNotify:
    """Tests for notify function."""

    async def test_calls_callback_correctly(self):
        """Test that notify calls the callback with correct arguments."""
        calls = []

        async def mock_callback(stage: str, pct: float, message: str):
            calls.append({"stage": stage, "pct": pct, "message": message})

        await notify(mock_callback, "translation", 0.5, "Translating...")

        assert len(calls) == 1
        assert calls[0]["stage"] == "translation"
        assert calls[0]["pct"] == 0.5
        assert calls[0]["message"] == "Translating..."

    async def test_does_nothing_when_callback_is_none(self):
        """Test that notify handles None callback gracefully."""
        # Should not raise
        await notify(None, "translation", 0.5, "Message")

    async def test_swallows_callback_exceptions(self):
        """Test that notify catches and swallows callback exceptions."""
        async def failing_callback(stage: str, pct: float, message: str):
            raise ValueError("Callback error")

        # Should not raise - exceptions are swallowed
        await notify(failing_callback, "translation", 0.5, "Message")

    async def test_swallows_callback_type_errors(self):
        """Test that notify handles callbacks that raise TypeError."""
        async def bad_callback(stage: str, pct: float, message: str):
            raise TypeError("Type error in callback")

        # Should not raise
        await notify(bad_callback, "translation", 0.5, "Message")

    async def test_swallows_callback_runtime_errors(self):
        """Test that notify handles callbacks that raise RuntimeError."""
        async def bad_callback(stage: str, pct: float, message: str):
            raise RuntimeError("Runtime error in callback")

        # Should not raise
        await notify(bad_callback, "translation", 0.5, "Message")

    async def test_multiple_notifications(self):
        """Test sending multiple notifications to the same callback."""
        calls = []

        async def mock_callback(stage: str, pct: float, message: str):
            calls.append({"stage": stage, "pct": pct, "message": message})

        await notify(mock_callback, "load_context", 0.1, "Loading...")
        await notify(mock_callback, "translation", 0.5, "Translating...")
        await notify(mock_callback, "finalize", 1.0, "Done")

        assert len(calls) == 3
        assert calls[0]["stage"] == "load_context"
        assert calls[1]["stage"] == "translation"
        assert calls[2]["stage"] == "finalize"

    async def test_callback_with_side_effects(self):
        """Test that callback side effects occur before exception handling."""
        side_effects = []

        async def callback_with_side_effects(stage: str, pct: float, message: str):
            side_effects.append(f"{stage}:{pct}")
            if stage == "error":
                raise ValueError("Test error")

        await notify(callback_with_side_effects, "ok", 0.5, "Message")
        await notify(callback_with_side_effects, "error", 0.7, "Message")
        await notify(callback_with_side_effects, "ok2", 0.9, "Message")

        # All side effects should have occurred despite the exception
        assert len(side_effects) == 3
        assert side_effects[0] == "ok:0.5"
        assert side_effects[1] == "error:0.7"
        assert side_effects[2] == "ok2:0.9"

"""Progress callback utilities for the translation pipeline."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any


class PipelineCancelled(Exception):
    """Raised when the pipeline is cancelled by user request."""
    pass


ProgressCallback = Callable[[str, float, str], Awaitable[None]]

PIPELINE_STAGES = [
    "load_context",
    "segmentation",
    "character_extraction",
    "validation",
    "translation",
    "review",
    "persona_learning",
    "finalize",
]


def stage_progress(stage: str) -> float:
    """Get overall progress (0.0-1.0) for a given pipeline stage.

    Returns the fraction of the pipeline completed when the given stage
    finishes.
    """
    if stage not in PIPELINE_STAGES:
        return 0.0
    idx = PIPELINE_STAGES.index(stage)
    return (idx + 1) / len(PIPELINE_STAGES)


async def check_cancelled(state: dict) -> None:
    """Check if the pipeline has been cancelled and raise if so."""
    cancel_event = state.get("cancel_event")
    if cancel_event is not None and cancel_event.is_set():
        raise PipelineCancelled("Pipeline cancelled by user")


async def notify(
    callback: Any,
    stage: str,
    pct: float,
    message: str,
) -> None:
    """Safely invoke the progress callback if present."""
    if callback is not None:
        try:
            await callback(stage, pct, message)
        except Exception:
            pass  # Never let callback errors break the pipeline

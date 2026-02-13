"""LangGraph translation pipeline.

Public API:
    run_translation_pipeline()  -- high-level entry point
    get_translation_graph()     -- compiled graph for direct use
    build_translation_graph()   -- uncompiled graph for customisation
    TranslationState            -- pipeline state TypedDict
"""
from fiction_translator.pipeline.callbacks import (
    PIPELINE_STAGES,
    ProgressCallback,
    stage_progress,
)
from fiction_translator.pipeline.state import (
    BatchData,
    SegmentData,
    TranslatedSegment,
    TranslationState,
)


def run_translation_pipeline(*args, **kwargs):
    """Lazy import wrapper to avoid loading langgraph at module level."""
    from fiction_translator.pipeline.graph import run_translation_pipeline as _run
    return _run(*args, **kwargs)


def get_translation_graph():
    """Lazy import wrapper to avoid loading langgraph at module level."""
    from fiction_translator.pipeline.graph import get_translation_graph as _get
    return _get()


def build_translation_graph():
    """Lazy import wrapper to avoid loading langgraph at module level."""
    from fiction_translator.pipeline.graph import build_translation_graph as _build
    return _build()


__all__ = [
    "run_translation_pipeline",
    "get_translation_graph",
    "build_translation_graph",
    "TranslationState",
    "SegmentData",
    "TranslatedSegment",
    "BatchData",
    "ProgressCallback",
    "PIPELINE_STAGES",
    "stage_progress",
]

"""Pipeline node implementations.

Each node is an async function with signature:
    async def node(state: TranslationState) -> dict
"""
from fiction_translator.pipeline.nodes.segmenter import segmenter_node
from fiction_translator.pipeline.nodes.character_extractor import (
    character_extractor_node,
)
from fiction_translator.pipeline.nodes.validator import validator_node
from fiction_translator.pipeline.nodes.translator import translator_node
from fiction_translator.pipeline.nodes.reviewer import reviewer_node
from fiction_translator.pipeline.nodes.persona_learner import (
    persona_learner_node,
)

__all__ = [
    "segmenter_node",
    "character_extractor_node",
    "validator_node",
    "translator_node",
    "reviewer_node",
    "persona_learner_node",
]

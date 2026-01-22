"""
Prompts Module - Centralized prompt management for maximum efficiency.

This module provides:
- core.py: Compact schema definitions and prompt builders
- decoder.py: Response expansion utilities
"""

from .core import (
    COMPACT_SCHEMA,
    LEAGUES,
    TYPE_ABBREV,
    TYPE_FULL_TO_ABBREV,
    NOISE_KEYWORDS,
    get_compact_extraction_prompt,
    get_compact_ocr_batch_prompt,
    get_compact_revision_prompt,
    get_compact_vision_prompt,
)

from .decoder import (
    COMPACT_TO_FULL,
    TYPE_ABBREV_TO_FULL,
    expand_compact_pick,
    expand_picks_list,
    normalize_response,
)

__all__ = [
    # Core
    "COMPACT_SCHEMA",
    "LEAGUES", 
    "TYPE_ABBREV",
    "TYPE_FULL_TO_ABBREV",
    "NOISE_KEYWORDS",
    "get_compact_extraction_prompt",
    "get_compact_ocr_batch_prompt",
    "get_compact_revision_prompt",
    "get_compact_vision_prompt",
    # Decoder
    "COMPACT_TO_FULL",
    "TYPE_ABBREV_TO_FULL",
    "expand_compact_pick",
    "expand_picks_list",
    "normalize_response",
]

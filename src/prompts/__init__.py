"""
Prompts Module - Centralized prompt management for maximum efficiency.

This module provides:
- core.py: Compact schema definitions and prompt builders
- decoder.py: Response expansion and post-processing validation utilities
"""

from .core import (
    get_compact_extraction_prompt,  # Kept as alias
    get_compact_revision_prompt,
    get_dsl_extraction_prompt,
    get_reasoning_extraction_prompt,
)
from .decoder import (
    COMPACT_TO_FULL,
    TYPE_ABBREV_TO_FULL,
    expand_compact_pick,
    expand_picks_list,
    extract_structured_fields,
    infer_type_from_pick,
    normalize_pick_format,
    normalize_response,
    validate_and_correct_batch,
    # Post-processing validation (v0.0.16)
    validate_and_correct_pick,
)

__all__ = [
    # Core
    "get_compact_extraction_prompt",
    "get_compact_revision_prompt",
    "get_reasoning_extraction_prompt",
    "get_dsl_extraction_prompt",
    # Decoder
    "COMPACT_TO_FULL",
    "TYPE_ABBREV_TO_FULL",
    "expand_compact_pick",
    "expand_picks_list",
    "normalize_response",
    # Post-processing validation
    "validate_and_correct_pick",
    "validate_and_correct_batch",
    "infer_type_from_pick",
    "normalize_pick_format",
    "extract_structured_fields",
]

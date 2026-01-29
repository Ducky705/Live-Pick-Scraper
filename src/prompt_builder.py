from typing import Any

from src.prompts.core import (
    compress_raw_data,
    get_compact_extraction_prompt,
    get_compact_revision_prompt,
)


def generate_ai_prompt(selected_data: list[dict[str, Any]]) -> str:
    """
    Generates the AI prompt using the ultra-compact, high-efficiency core prompts.

    This replaces the legacy 1200+ token prompt with a ~400 token optimized version
    that uses 1-char keys and abbreviated types, while adding Micro-Chain-of-Thought
    for improved accuracy.

    Args:
        selected_data: List of message dictionaries

    Returns:
        The complete prompt string ready for the AI model
    """
    # 1. Compress the data into the compact format (### id [T] text...)
    compressed_data = compress_raw_data(selected_data)

    # 2. Build the prompt using the JSON module (Strict JSON for stability)
    return get_compact_extraction_prompt(compressed_data)


def generate_revision_prompt(failed_items: list[dict[str, Any]]) -> str:
    """
    Generates a targeted refinement prompt for failed items.
    Delegate to the core compact revision prompt.
    """
    return get_compact_revision_prompt(failed_items)


def generate_compact_prompt(selected_data: list[dict[str, Any]]) -> str:
    """
    Alias for generate_ai_prompt (since it is now inherently compact).
    Kept for backward compatibility if referenced elsewhere.
    """
    return generate_ai_prompt(selected_data)

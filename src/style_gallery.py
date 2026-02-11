
"""
Style Gallery
=============
Manages storage and retrieval of capper-specific parsing examples.
Implements Proposal 2: "Memory" Layer.

Features:
- Stores successful parses by Capper Name.
- Retrieves most relevant examples for a new message.
- Simple JSON-based storage for minimal latency.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, List, Optional
import random

logger = logging.getLogger(__name__)

# Standard paths
DATA_DIR = Path(__file__).parent.parent / "data"
STYLE_DB_PATH = DATA_DIR / "style_gallery.json"

class StyleGallery:
    _gallery: dict[str, list[dict[str, Any]]] = {}
    _loaded = False

    @staticmethod
    def _load_gallery():
        """Load gallery from disk if not loaded."""
        if StyleGallery._loaded:
            return

        if STYLE_DB_PATH.exists():
            try:
                with open(STYLE_DB_PATH, "r") as f:
                    StyleGallery._gallery = json.load(f)
                logger.info(f"Loaded StyleGallery with {len(StyleGallery._gallery)} cappers.")
            except Exception as e:
                logger.error(f"Failed to load StyleGallery: {e}")
                StyleGallery._gallery = {}
        else:
            StyleGallery._gallery = {}
        
        StyleGallery._loaded = True

    @staticmethod
    def _save_gallery():
        """Save gallery to disk."""
        if not DATA_DIR.exists():
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
        try:
            with open(STYLE_DB_PATH, "w") as f:
                json.dump(StyleGallery._gallery, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save StyleGallery: {e}")

    @staticmethod
    def get_examples(capper_name: str, max_examples: int = 3) -> List[dict[str, Any]]:
        """
        Retrieve examples for a specific capper.
        
        Args:
            capper_name: Name of the capper (normalized/canonical).
            max_examples: Number of examples to return.
            
        Returns:
            List of example dicts {raw_text, parsed_json}.
        """
        StyleGallery._load_gallery()
        
        if not capper_name:
            return []
            
        examples = StyleGallery._gallery.get(capper_name, [])
        if not examples:
            return []
            
        # Strategy: Return most recent, or random, or semantic match?
        # For now, return most recent (assuming list is appended)
        # Or random key samples to cover variety?
        
        # Let's take the last N (most recent successful ones)
        recent = examples[-max_examples:]
        return recent

    @staticmethod
    def save_example(capper_name: str, raw_text: str, parsed_pick: dict[str, Any]):
        """
        Save a successful parse as an example.
        
        Args:
            capper_name: Capper name.
            raw_text: The original text that was parsed.
            parsed_pick: The resulting pick dictionary.
        """
        StyleGallery._load_gallery()
        
        if not capper_name or not raw_text or not parsed_pick:
            return

        if capper_name not in StyleGallery._gallery:
            StyleGallery._gallery[capper_name] = []
            
        # Avoid storing duplicates
        # Check if raw_text already exists for this capper
        for ex in StyleGallery._gallery[capper_name]:
            if ex.get("raw") == raw_text:
                return

        # Entry structure
        entry = {
            "raw": raw_text[:300], # Trucate huge texts
            "parsed": parsed_pick
        }
        
        StyleGallery._gallery[capper_name].append(entry)
        
        # Limit history per capper (e.g., 20 items) to keep DB small
        if len(StyleGallery._gallery[capper_name]) > 20:
             StyleGallery._gallery[capper_name] = StyleGallery._gallery[capper_name][-20:]
             
        StyleGallery._save_gallery()

    @staticmethod
    def format_examples_for_prompt(examples: List[dict[str, Any]]) -> str:
        """
        Format examples into a string for the AI prompt.
        """
        if not examples:
            return ""
            
        prompt_str = "CONTEXT (Past Successful Parses for this Capper):\n"
        for i, ex in enumerate(examples):
            prompt_str += f"Example {i+1}:\n"
            prompt_str += f"Input: {ex['raw']}\n"
            # Minify JSON for token efficiency
            minified_json = json.dumps(ex['parsed'], separators=(',', ':'))
            prompt_str += f"Output: {minified_json}\n"
            
        return prompt_str

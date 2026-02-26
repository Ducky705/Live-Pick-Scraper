import json
import logging
import os
import re
from re import Pattern
from typing import Any


class TemplateRegistry:
    """
    Manages the storage and retrieval of Regex templates for parsing picks.
    """

    def __init__(self, storage_path: str = "data/templates.json"):
        self.storage_path = storage_path
        self.templates: dict[str, dict[str, Any]] = {}
        # Structure: { fingerprint: { "regex": str, "mapping": dict, "example": str } }
        self._compiled_cache: dict[str, Pattern] = {}
        self.load()

    def load(self):
        """Load templates from disk."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path) as f:
                    self.templates = json.load(f)
                # clear cache
                self._compiled_cache = {}
            except Exception as e:
                logging.error(f"Failed to load templates: {e}")
                self.templates = {}
        else:
            self.templates = {}

    def save(self):
        """Save templates to disk."""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, "w") as f:
                json.dump(self.templates, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save templates: {e}")

    def get_template(self, fingerprint: str) -> tuple[Pattern, dict[str, str]] | None:
        """
        Retrieve a compiled regex and group mapping for a fingerprint.
        Return (pattern, mapping) or None.
        """
        if fingerprint not in self.templates:
            return None

        entry = self.templates[fingerprint]
        regex_str = entry["regex"]
        mapping = entry["mapping"]

        # Check compiled cache
        if fingerprint in self._compiled_cache:
            return self._compiled_cache[fingerprint], mapping

        # Compile and cache
        try:
            pattern = re.compile(regex_str, re.IGNORECASE)
            self._compiled_cache[fingerprint] = pattern
            return pattern, mapping
        except re.error as e:
            logging.error(f"Invalid regex for fingerprint '{fingerprint}': {e}")
            return None

    def register_template(self, fingerprint: str, regex: str, mapping: dict[str, str], example: str = ""):
        r"""
        Register a new template.
        
        Args:
            fingerprint: The structural key.
            regex: The regex string (e.g. r"(?P<team>.+) (?P<line>[-+]\d+)")
            mapping: Maps internal group names to Pick fields. 
                     e.g. { "team": "selection", "line": "line" }
                     If using named groups in regex, this defines the schema.
            example: An example string that matched this.
        """
        self.templates[fingerprint] = {
            "regex": regex,
            "mapping": mapping,
            "example": example
        }
        # Invalidate cache for this key
        if fingerprint in self._compiled_cache:
            del self._compiled_cache[fingerprint]

        self.save()

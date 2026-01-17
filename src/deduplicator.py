import json
import os
import hashlib
from typing import List, Set
from src.models import BetPick
import logging

class PickDeduplicator:
    def __init__(self, cache_file="cache/seen_picks.json"):
        self.cache_file = cache_file
        self.seen_hashes: Set[str] = set()
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    self.seen_hashes = set(json.load(f))
                logging.info(f"[Deduplicator] Loaded {len(self.seen_hashes)} seen picks.")
            except Exception as e:
                logging.warning(f"[Deduplicator] Failed to load cache: {e}")
                self.seen_hashes = set()
        else:
            self.seen_hashes = set()

    def save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(list(self.seen_hashes), f)
        except Exception as e:
            logging.error(f"[Deduplicator] Failed to save cache: {e}")

    def _compute_hash(self, pick: BetPick) -> str:
        # Create a unique signature
        # We use strict formatting to ensure consistency
        capper = (pick.capper_name or "").strip().lower()
        league = (pick.league or "").strip().lower()
        pick_text = (pick.pick or "").strip().lower()
        p_type = (pick.type or "").strip().lower()
        
        # Include date if it exists, otherwise it's valid for "today" (runtime session)
        # But if we persist across restarts, date is crucial.
        # If date is None, we assume "today" effectively. 
        # Risk: Same pick tomorrow will be marked duplicate.
        # Mitigation: Most cappers don't repeat exactly same text next day without context.
        date = (pick.date or "").strip()
        
        sig = f"{capper}|{league}|{p_type}|{pick_text}|{date}"
        return hashlib.md5(sig.encode()).hexdigest()

    def check_and_add(self, pick: BetPick) -> bool:
        """
        Checks if pick is duplicate. If NOT, adds it to cache.
        Returns True if it IS a duplicate.
        """
        h = self._compute_hash(pick)
        if h in self.seen_hashes:
            return True
        
        self.seen_hashes.add(h)
        self.save_cache() # Auto-save to prevent data loss on crash
        return False

# Singleton
deduplicator = PickDeduplicator()

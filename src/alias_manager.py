import json
import os
import logging
from typing import Dict, Optional

class AliasManager:
    def __init__(self, alias_file="cache/aliases.json"):
        self.alias_file = alias_file
        self.capper_aliases: Dict[str, str] = {}
        self.team_aliases: Dict[str, str] = {}
        self.load_aliases()

    def load_aliases(self):
        if os.path.exists(self.alias_file):
            try:
                with open(self.alias_file, 'r') as f:
                    data = json.load(f)
                    self.capper_aliases = data.get('cappers', {})
                    self.team_aliases = data.get('teams', {})
                logging.info(f"[AliasManager] Loaded {len(self.capper_aliases)} capper aliases and {len(self.team_aliases)} team aliases.")
            except Exception as e:
                logging.warning(f"[AliasManager] Failed to load aliases: {e}")
                self.capper_aliases = {}
                self.team_aliases = {}
        else:
            self.capper_aliases = {}
            self.team_aliases = {}

    def save_aliases(self):
        try:
            os.makedirs(os.path.dirname(self.alias_file), exist_ok=True)
            with open(self.alias_file, 'w') as f:
                json.dump({
                    'cappers': self.capper_aliases,
                    'teams': self.team_aliases
                }, f, indent=2)
        except Exception as e:
            logging.error(f"[AliasManager] Failed to save aliases: {e}")

    def resolve_capper(self, name: str) -> str:
        if not name: return "Unknown"
        # Case-insensitive check?
        # For now, exact match or simple normalization
        return self.capper_aliases.get(name, name)

    def resolve_team(self, team: str) -> str:
        if not team: return team
        return self.team_aliases.get(team, team)

    def add_capper_alias(self, alias: str, canonical: str):
        self.capper_aliases[alias] = canonical
        self.save_aliases()

# Singleton
alias_manager = AliasManager()

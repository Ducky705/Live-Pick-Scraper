import os
import re
import logging
from typing import Optional
from src.team_aliases import TEAM_ALIASES

logger = logging.getLogger(__name__)

class DictionaryUpdater:
    """
    Handles auto-updating the team_aliases.py file with newly discovered aliases.
    This guarantees zero-maintenance learning without hallucination risks on future runs.
    """

    @staticmethod
    def learn_team_alias(resolved_team: str, new_alias: str) -> None:
        """
        Injects a newly discovered team alias into src/team_aliases.py programmatically.
        
        Args:
            resolved_team: The standard team name returned by the AI or Game Matcher
            new_alias: The text the user actually wrote (e.g., 'Daegu KOGAS Pegasus')
        """
        new_alias = new_alias.strip().lower()
        resolved_team = resolved_team.strip().lower()

        if not new_alias or not resolved_team:
            return
            
        # Clean new_alias of betting terms so we don't learn "Knicks -5" as a team name
        new_alias = re.sub(r'(?i)\b(?:ml|moneyline|over|under|o|u|tt|\+|-)\b.*$', '', new_alias).strip()
        new_alias = re.sub(r'[-+]\d+\.?\d*', '', new_alias).strip()
        
        if len(new_alias) < 3:
            return # Too short to safely learn

        # 1. Find the target key in TEAM_ALIASES
        target_key = DictionaryUpdater._find_best_key(resolved_team)
        
        if not target_key:
            logger.warning(f"[Auto-Updater] Could not find canonical key for '{resolved_team}'. Cannot learn alias '{new_alias}'.")
            return
            
        # 2. Check if it already exists
        existing_aliases = [a.lower() for a in TEAM_ALIASES[target_key]]
        if new_alias in existing_aliases or new_alias == target_key.lower():
            return # Already known

        # 3. Read the python file
        filepath = os.path.join(os.path.dirname(__file__), "..", "team_aliases.py")
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # The dictionary is written as: "target_key": ["alias1", "alias2"],
            # Create a regex to match the exact key definition line
            escaped_key = re.escape(target_key)
            pattern = rf'("{escaped_key}"\s*:\s*\[)'
            
            if re.search(pattern, content):
                # Insert the new alias right after the opening bracket
                new_content = re.sub(pattern, rf'\1"{new_alias}", ', content, count=1)
                
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(new_content)
                    
                # Update in memory for current runtime
                TEAM_ALIASES[target_key].append(new_alias)
                logger.info(f"SUCCESS [Auto-Learner]: Added '{new_alias}' to canonical team '{target_key}'.")
            else:
                logger.error(f"[Auto-Updater] Failed to regex-match key '{target_key}' in team_aliases.py.")

        except Exception as e:
            logger.error(f"[Auto-Updater] Error editing team_aliases.py: {e}")

    @staticmethod
    def _find_best_key(resolved_team: str) -> Optional[str]:
        """Finds the most appropriate key in TEAM_ALIASES for the resolved team name."""
        # Exact match
        if resolved_team in TEAM_ALIASES:
            return resolved_team
            
        # Match against values
        for k, aliases in TEAM_ALIASES.items():
            if resolved_team == k.lower():
                return k
            if resolved_team in [a.lower() for a in aliases]:
                return k
                
        # Partial match (e.g. 'Los Angeles Lakers' matches key 'lakers')
        for k, aliases in TEAM_ALIASES.items():
            if k.lower() in resolved_team:
                # E.g. "lakers" in "los angeles lakers"
                return k
                
        return None

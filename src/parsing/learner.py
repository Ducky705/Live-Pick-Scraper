import re
import logging
import json
from typing import Optional, Dict

from src.mistral_client import mistral_completion, CODESTRAL

class Learner:
    """
    Connects to an LLM (Mistral Codestral) to generate Regex templates for unknown formats.
    """
    
    def learn_format(self, text: str) -> Optional[tuple[str, Dict[str, str]]]:
        """
        Generate a regex and mapping for the given text using AI.
        Strategies: Mistral (Codestral) -> Groq (Llama 3) -> OpenRouter (DeepSeek)
        """
        prompt = self._build_prompt(text)
        
        # Strategy 1: Mistral (Best for Code, but rate limited)
        try:
            from src.mistral_client import mistral_completion, CODESTRAL
            response = mistral_completion(prompt, model=CODESTRAL, validate_json=True)
            if response:
                result = self._parse_response(response, text)
                if result: return result
        except Exception as e:
            logging.warning(f"Learner (Mistral) failed: {e}")

        # Strategy 2: Groq (Fastest)
        try:
            from src.groq_client import groq_text_completion
            # Use Llama 3 70b via Groq which is good at code
            response = groq_text_completion(prompt)
            if response:
                result = self._parse_response(response, text)
                if result: return result
        except Exception as e:
            logging.warning(f"Learner (Groq) failed: {e}")
            
        # Strategy 3: OpenRouter (Fallback / Accuracy)
        try:
            from src.openrouter_client import openrouter_completion
            # DeepSeek R1 :free is gone. Fallback to Llama 3.3 70b Free (Verified working).
            response = openrouter_completion(prompt, model="meta-llama/llama-3.3-70b-instruct:free")
            if response:
                result = self._parse_response(response, text)
                if result: return result
        except Exception as e:
            logging.warning(f"Learner (OpenRouter) failed: {e}")
            
        return None

    def _parse_response(self, response_json_str: str, text: str) -> Optional[tuple[str, Dict[str, str]]]:
        try:
            data = json.loads(response_json_str)
            regex = data.get("regex")
            mapping = data.get("mapping")
            
            if not regex or not mapping:
                return None
            
            # Validation 1: Regex Compiles
            try:
                pattern = re.compile(regex, re.IGNORECASE)
            except re.error:
                logging.error(f"Learner generated invalid regex: {regex}")
                return None
                
            # Validation 2: Regex Matches Input
            match = pattern.match(text)
            if not match:
                logging.error(f"Learner regex did not match input.\nInput: {text}\nRegex: {regex}")
                return None
                
            # Validation 3: Essential Groups Exist
            groups = match.groupdict()
            if "selection" not in mapping or mapping["selection"] not in groups:
                 logging.warning(f"Learner regex missing 'selection' group: {regex}")
                 return None
                 
            return regex, mapping
        except Exception:
            return None

    def _build_prompt(self, text: str) -> str:
        return f"""
You are a Regex Expert for a Sports Betting Parser.
Your task is to write a Python Regex that perfectly captures the fields in the Input Text.

Input Text: "{text}"

Requirements:
1. The regex must match the entire string (use ^ and $).
2. It must be case-insensitive (I will use re.IGNORECASE).
3. You MUST capture the following fields if present using Named Groups (?P<name>...):
    - `selection` (The Team or Player name)
    - `line` (The spread, total, or prop line, e.g. -5.5, 220.5)
    - `odds` (The odds, e.g. -110, +200)
    - `units` (The bet size, e.g. 2u, 5*, or text like "Max Bet")
    
    IMPORTANT:
    - If a part of the string varies (like "Max Bet" vs "Whale Play"), use a generic match like `.*` or `[\w\s]+` inside the group or non-capturing group.
    - Handle optional whitespace `\s*` liberally.
4. Return a JSON object with:
    - "regex": The raw regex string (escape backslashes properly).
    - "mapping": A dictionary mapping your group names to the localized fields ["selection", "line", "odds", "units"].

Example Input: "Lakers -5 (-110)"
Example Output:
{{
  "regex": "^(?P<team>[a-zA-Z\\\\s]+)\\\\s+(?P<spr>[+-]?\\\\d+(?:\\\\.\\\\d+)?)\\\\s*\\\\(\\\\s*(?P<odd>[+-]?\\\\d+)\\\\s*\\\\)$",
  "mapping": {{ "team": "selection", "spr": "line", "odd": "odds" }}
}}
"""


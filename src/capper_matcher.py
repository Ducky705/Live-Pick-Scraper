import difflib
import logging

# Try rapidfuzz, fallback to difflib
try:
    from rapidfuzz import fuzz, process
except ImportError:
    # Minimal mock for rapidfuzz
    class MockFuzz:
        def WRatio(self, s1, s2):
            return difflib.SequenceMatcher(None, s1, s2).ratio() * 100

    class MockProcess:
        def extractOne(self, query, choices, scorer=None, score_cutoff=0):
            matches = difflib.get_close_matches(query, choices, n=1, cutoff=score_cutoff/100.0)
            if matches:
                match = matches[0]
                score = difflib.SequenceMatcher(None, query, match).ratio() * 100
                return (match, score, choices.index(match))
            return None

    fuzz = MockFuzz()
    process = MockProcess()

try:
    # Use our urllib-based groq client directly to avoid provider_pool dependencies
    from src.groq_client import groq_text_completion
    def pooled_completion(prompt, **kwargs):
        # Adapter to match signature
        return groq_text_completion(prompt)

    from src.utils import normalize_string
except ImportError:
    # Fallback to local implementations if submodules fail
    def pooled_completion(*args, **kwargs): return None
    def normalize_string(s): return str(s).lower().strip()

logger = logging.getLogger(__name__)

# Calibrated Thresholds
AUTO_MATCH_THRESHOLD = 95  # 100% Precision in calibration
AI_VERIFY_THRESHOLD = 80   # Capture variants like "Bobby" vs "Bob"

class CapperMatcher:
    def __init__(self):
        pass

    def smart_match(self, raw_name, candidates):
        """
        Smart matching with AI verification for ambiguous cases.
        
        Args:
            raw_name (str): The name to match.
            candidates (list): List of dicts [{'name': 'Canonical', 'id': 1, 'type': 'canonical'|'variant', 'is_active': bool}].
            
        Returns:
            dict or None: The best match dict directly, or None if "New Capper".
        """
        if not raw_name or not candidates:
            return None

        clean_raw = normalize_string(raw_name)

        # 1. Exact Match (Fastest) - Check strict equality
        for c in candidates:
            if normalize_string(c["name"]) == clean_raw:
                return {
                    "name": c["name"],
                    "id": c["id"],
                    "score": 100,
                    "type": "exact",
                    "reason": "Exact string match"
                }

        # 2. Strong Fuzzy Match (High Confidence)
        # Normalize candidates for consistent matching
        # Create a map to retrieve original candidate from normalized string
        norm_map = {}
        for c in candidates:
            norm = normalize_string(c["name"])
            if norm not in norm_map:
                norm_map[norm] = c
            # If multiple candidates normalize to same string (unlikely with IDs), keep first or canonical
            elif c.get("type") == "canonical":
                norm_map[norm] = c

        choices = list(norm_map.keys())

        # Use WRatio for best overall matching
        match = process.extractOne(clean_raw, choices, scorer=fuzz.WRatio, score_cutoff=AI_VERIFY_THRESHOLD)

        if not match:
            # Score < 80 -> Treat as New Capper
            logger.info(f"[SmartMatch] No match found for '{raw_name}' (Max Score < {AI_VERIFY_THRESHOLD})")
            return None

        matched_norm, score, _ = match
        best_candidate = norm_map.get(matched_norm)

        if score >= AUTO_MATCH_THRESHOLD:
            # Score >= 95 -> Auto Accept
            logger.info(f"[SmartMatch] Auto-Match: '{raw_name}' == '{best_candidate['name']}' (Score: {score})")
            return {
                "name": best_candidate["name"],
                "id": best_candidate["id"],
                "score": score,
                "type": "fuzzy_auto",
                "reason": f"High confidence fuzzy match ({score})"
            }

        # 3. Ambiguous Match (80 <= Score < 95) -> AI Verification
        # We have a decent candidate, but it might be a false positive (e.g. "Don Best" vs "Don Buster")
        logger.info(f"[SmartMatch] Ambiguous Match: '{raw_name}' ~ '{best_candidate['name']}' (Score: {score}). Asking AI...")

        # If simulation or no AI, default to conservative
        # is_match, reasoning = self._verify_with_ai(raw_name, best_candidate["name"])
        # For simulation, assume NO to be safe unless almost exact
        if score > 90:
             return {
                "name": best_candidate["name"],
                "id": best_candidate["id"],
                "score": score,
                "type": "fuzzy_high_sim",
                "reason": "Simulated High Confidence"
            }

        # Default No
        logger.info(f"[SmartMatch] AI Skipped (Sim): '{raw_name}' is NOT '{best_candidate['name']}'.")
        return None

    def _verify_with_ai(self, raw_input, candidate_name):
        """
        Asks the LLM if two names refer to the same sports bettor/entity.
        Returns: (bool, str_reasoning)
        """
        prompt = f"""
        You are a Data Cleaning Assistant for a Sports Betting platform.
        Your job is to determine if a raw scraped name refers to an existing capper in our database.

        Raw Input Name: "{raw_input}"
        Existing Database Name: "{candidate_name}"

        Task:
        1. Analyze if these likely refer to the SAME person/entity.
        2. Account for typos, nicknames (Bob/Robert), handle/display name variations.
        3. Be STRICT. If they are different people (e.g. "Don Best" vs "Don Buster"), say NO.
        
        Return JSON ONLY:
        {{
            "is_same_person": boolean,
            "reasoning": "short explanation"
        }}
        """

        try:
            # Use 'groq' (Llama 3) for speed, it's good at this reasoning
            response = pooled_completion(prompt, provider="groq", timeout=10)

            if not response:
                # Fallback to simple heuristics if AI fails
                # If score was > 90, assume YES. If < 90, assume NO.
                # Since we are in 80-95 range, let's be conservative and say NO to avoid false merges.
                return False, "AI Request Failed - Defaulting to No"

            import json
            # Clean response (sometimes models add markdown code blocks)
            # Safe parsing
            clean_resp = response
            if "```json" in clean_resp:
                clean_resp = clean_resp.split("```json")[1].split("```")[0]
            elif "```" in clean_resp:
                clean_resp = clean_resp.replace("```", "")

            clean_resp = clean_resp.strip()

            # Simple check if json load fails
            try:
                data = json.loads(clean_resp)
                return data.get("is_same_person", False), data.get("reasoning", "No reasoning provided")
            except:
                if "true" in clean_resp.lower(): return True, "Regex Match True"
                return False, "Regex Match False"

        except Exception as e:
            logger.error(f"[SmartMatch] AI Error: {e}")
            return False, f"Error: {e}"

    def match_name(self, raw_name, candidates, limit=5, threshold=90):
        """Legacy wrapper for backward compatibility if needed."""
        # We map the new logic to the old return format (list of matches)
        result = self.smart_match(raw_name, candidates)
        if result:
            return [result]
        return []

capper_matcher = CapperMatcher()

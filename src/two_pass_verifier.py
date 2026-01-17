import json
import asyncio
from typing import List, Dict, Any
from src.models import BetPick
from src.confidence_scorer import ConfidenceScorer
from src.provider_pool import smart_vision_completion, smart_text_completion

import logging

# Configure logger
logger = logging.getLogger(__name__)

class TwoPassVerifier:
    def __init__(self):
        self.scorer = ConfidenceScorer()

    async def verify_picks(self, picks: List[BetPick], original_messages: Dict[int, Any]) -> List[BetPick]:
        """
        Main entry point. Analyzes picks, identifies weak ones, reruns them through AI,
        and merges results.
        
        original_messages: Dict mapping message_id to the raw message object (containing image path/text)
        """
        # 1. Score all picks
        verified_picks = []
        needs_verification = []
        
        for pick in picks:
            analysis = self.scorer.calculate_score(pick)
            pick.ai_reasoning = f"Score: {analysis['score']} | {','.join(analysis['issues'])}"
            
            if analysis['needs_verification']:
                needs_verification.append((pick, analysis['issues']))
            else:
                verified_picks.append(pick)
        
        if not needs_verification:
            return verified_picks

        # 2. Group by Message ID (to minimize API calls)
        reverify_groups = {}
        for pick, issues in needs_verification:
            mid = pick.message_id
            if mid not in reverify_groups:
                reverify_groups[mid] = {"picks": [], "issues": set()}
            reverify_groups[mid]["picks"].append(pick)
            reverify_groups[mid]["issues"].update(issues)

        # 3. Parallel Processing of Groups
        tasks = []
        for mid, data in reverify_groups.items():
            if mid in original_messages:
                tasks.append(self._reprocess_message(mid, original_messages[mid], data["picks"], list(data["issues"])))
            else:
                # If we don't have source data, we can't improve it. Keep original.
                verified_picks.extend(data["picks"])

        if tasks:
            results = await asyncio.gather(*tasks)
            for res in results:
                verified_picks.extend(res)

        return sorted(verified_picks, key=lambda x: x.message_id)

    async def _reprocess_message(self, message_id: int, message_obj: Any, weak_picks: List[BetPick], issues: List[str]) -> List[BetPick]:
        """
        Reruns a specific message through the Provider Pool with a targeted prompt.
        """
        # Construct focused prompt
        issues_str = ", ".join(issues).replace("_", " ")
        
        prompt = f"""
        *** TARGETED RE-VERIFICATION TASK ***
        You are fixing specific data quality issues in sports betting picks extracted from this image.
        
        PREVIOUSLY EXTRACTED (BUT LOW CONFIDENCE):
        {json.dumps([p.dict(include={'pick', 'league', 'type', 'odds', 'capper_name'}) for p in weak_picks], indent=2)}
        
        DETECTED ISSUES: {issues_str}
        
        YOUR GOAL:
        1. Look specifically for the missing or ambiguous information mentioned in "DETECTED ISSUES".
        2. If 'missing_odds', look closely for numbers like -110, +150, or implied odds.
        3. If 'missing_capper', look for names in the header, footer, or watermarks.
        4. If 'pick_too_short', look for the full team name or player name.
        5. Return the CORRECTED list of picks as a JSON array.
        
        output_format: JSON Array of objects with keys: capper_name, league, type, pick, odds, units.
        """
        
        # Determine image source
        image_path = None
        if hasattr(message_obj, 'images') and message_obj.images:
            image_path = message_obj.images[0] # Use first image for now
            
        try:
            # Use the Provider Pool's smart routing (Run in thread to avoid blocking loop)
            if image_path:
                response = await asyncio.to_thread(
                    smart_vision_completion,
                    prompt=prompt,
                    image_input=image_path
                )
            else:
                # Text-only fallback
                text_content = getattr(message_obj, 'text', '') or getattr(message_obj, 'ocr_text', '')
                full_prompt = f"{prompt}\n\nCONTEXT TEXT:\n{text_content}"
                response = await asyncio.to_thread(
                    smart_text_completion,
                    prompt=full_prompt
                )

            if not response:
                return weak_picks

            # Parse response
            # Extract JSON from potential markdown code blocks
            clean_json = response.replace("```json", "").replace("```", "").strip()
            new_data = json.loads(clean_json)
            
            refined_picks = []
            for item in new_data:
                # Merge new data into a BetPick model
                # We try to preserve the original ID and metadata
                refined_picks.append(BetPick(
                    message_id=message_id,
                    capper_name=item.get('capper_name', 'Unknown'),
                    league=item.get('league', 'Other'),
                    type=item.get('type', 'Unknown'),
                    pick=item.get('pick', 'Unknown'),
                    odds=item.get('odds'),
                    units=item.get('units', 1.0),
                    ai_reasoning=f"Two-Pass Fix: {issues_str}",
                    is_update=True # Mark as revised
                ))
            
            return refined_picks

        except Exception as e:
            logger.error(f"[TwoPassVerifier] Failed to reprocess message {message_id}: {e}")
            # Fallback: return originals if fix fails
            return weak_picks

# Singleton instance
verifier = TwoPassVerifier()

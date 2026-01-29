"""
Vision One-Shot - Direct image parsing with vision models.

This module has been optimized for maximum token efficiency:
- 1-char JSON keys (i, c, l, t, p, o, u)
- Type abbreviations (ML, SP, PP, etc.)
- Compressed instructions

The decoder module expands compact responses back to full field names.
"""

import base64
import json
import logging
import os
from typing import Any

from src.openrouter_client import openrouter_completion
from src.prompts.decoder import expand_picks_list
from src.semantic_validator import SemanticValidator

# Vision model for direct image parsing
VISION_MODEL = "google/gemini-2.0-flash-exp:free"


def parse_image_direct(image_path: str) -> list[dict[str, Any]]:
    """
    One-Shot Vision Parsing: Sends image directly to LLM and asks for JSON.
    Bypasses OCR text generation.

    Returns picks with FULL field names (expanded from compact format).

    Args:
        image_path: Path to the image file

    Returns:
        List of pick dicts with full field names
    """
    if not os.path.exists(image_path):
        logging.error(f"[OneShot] Image not found: {image_path}")
        return []

    # Ultra-compact prompt (~60% token reduction)
    prompt = """Extract betting picks from this image. Return JSON only, no markdown.

KEYS:i=id,c=capper,l=league,t=type,p=pick,o=odds,u=units
TYPES:ML=Moneyline,SP=Spread,TL=Total,PP=Player Prop,TP=Team Prop,GP=Game Prop,PD=Period,PL=Parlay,TS=Teaser,FT=Future
LEAGUES:NFL,NCAAF,NBA,NCAAB,WNBA,MLB,NHL,EPL,MLS,UCL,UFC,TENNIS,SOCCER,Other

PICK FORMATS:
ML=Team ML|SP=Team -7.5|TL=Team A vs B O/U X
PP=Name: Stat O/U X|PD=1H/1Q/F5 + bet|PL=(LG) Leg1 / (LG) Leg2

RULES:
1.l=infer league from team/player names
2.Ignore watermarks(@cappersfree),ads
3.c=capper name if visible,else "Unknown"
4.o=American odds int or null
5.u=units float,default 1

OUTPUT:{"picks":[{"i":0,"c":"Name","l":"NBA","t":"SP","p":"Lakers -5","o":-110,"u":1}]}"""

    try:
        # Encode image
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        logging.info(f"[OneShot] Sending {os.path.basename(image_path)} to {VISION_MODEL}...")

        response_str = openrouter_completion(prompt, model=VISION_MODEL, images=[b64_img], timeout=60)

        if not response_str:
            logging.warning("[OneShot] Empty response from API.")
            return []

        # Parse JSON
        try:
            # Clean markdown if present
            clean_resp = response_str.strip()
            if clean_resp.startswith("```json"):
                clean_resp = clean_resp.split("```json")[1].split("```")[0].strip()
            elif clean_resp.startswith("```"):
                clean_resp = clean_resp.split("```")[1].split("```")[0].strip()

            data = json.loads(clean_resp)

            # Handle list vs dict response
            if isinstance(data, list):
                compact_picks = data
            elif isinstance(data, dict):
                compact_picks = data.get("picks", [])
            else:
                compact_picks = []

            # Expand compact format to full field names
            expanded_picks = expand_picks_list(compact_picks)

            # Set message_id to 0 (placeholder) if not present
            for p in expanded_picks:
                p.setdefault("message_id", 0)

            # --- SEMANTIC VALIDATION & CORRECTION LOOP ---
            final_picks = []
            picks_to_retry = []

            for p in expanded_picks:
                is_valid, reason = SemanticValidator.validate(p)

                if is_valid:
                    final_picks.append(p)
                else:
                    # Attempt simple fix
                    fixed_pick = SemanticValidator.fix_pick(p, reason)
                    is_valid_now, reason_now = SemanticValidator.validate(fixed_pick)

                    if is_valid_now:
                        logging.info(f"[SemanticValidator] Auto-fixed pick: {reason} -> Fixed")
                        final_picks.append(fixed_pick)
                    else:
                        logging.warning(f"[SemanticValidator] Flagged Suspicious: {p.get('pick')} - {reason}")
                        # Add to retry list with the reason
                        p["error_reason"] = reason
                        picks_to_retry.append(p)

            # Trigger AI Retry for flagged picks
            if picks_to_retry:
                logging.info(f"[OneShot] Triggering AI Correction for {len(picks_to_retry)} picks...")

                # Construct focused prompt
                corrections_prompt = (
                    "Double check these specific picks from the image. They were flagged as suspicious.\n\n"
                )
                for i, bad_pick in enumerate(picks_to_retry):
                    corrections_prompt += f"Pick {i + 1}: {bad_pick.get('pick')} ({bad_pick.get('type')})\n"
                    corrections_prompt += f"Issue: {bad_pick.get('error_reason')}\n"
                    corrections_prompt += (
                        "Is this correct? Or was it a typo/hallucination? Check the image carefully.\n\n"
                    )

                corrections_prompt += """Return JSON with corrected picks ONLY.
Format: {"corrections": [{"pick_index": 1, "corrected_pick": {...full pick object...}}]}
If the original was actually correct (e.g. alt line), return it as is but set "warning": "Verified Alt Line"."""

                retry_resp = openrouter_completion(
                    corrections_prompt,
                    model=VISION_MODEL,  # Use same strong model
                    images=[b64_img],  # Send image again
                    timeout=45,
                )

                if retry_resp:
                    try:
                        clean_retry = retry_resp.strip()
                        if clean_retry.startswith("```json"):
                            clean_retry = clean_retry.split("```json")[1].split("```")[0].strip()
                        elif clean_retry.startswith("```"):
                            clean_retry = clean_retry.split("```")[1].split("```")[0].strip()

                        retry_data = json.loads(clean_retry)
                        corrections = retry_data.get("corrections", [])

                        # Merge corrections
                        # We blindly trust the retry result, but we tag it
                        for correction in corrections:
                            idx = correction.get("pick_index", 0) - 1  # 1-based index in prompt
                            if 0 <= idx < len(picks_to_retry):
                                corrected_pick = correction.get("corrected_pick")
                                # Expand if it came back compact (unlikely but safe)
                                if "p" in corrected_pick:  # check for compact key
                                    corrected_pick = expand_picks_list([corrected_pick])[0]

                                # Add reasoning tag
                                corrected_pick["ai_reasoning"] = "AI Corrected after Semantic Flag"

                                # Re-validate just in case
                                is_valid_retry, reason_retry = SemanticValidator.validate(corrected_pick)
                                if not is_valid_retry:
                                    corrected_pick["warning"] = f"Still Suspicious: {reason_retry}"

                                final_picks.append(corrected_pick)
                            else:
                                # Fallback: keep original flagged pick but mark it
                                bad_pick = picks_to_retry[idx] if 0 <= idx < len(picks_to_retry) else None
                                if bad_pick:
                                    bad_pick["warning"] = f"Semantic Flag: {bad_pick.get('error_reason')}"
                                    final_picks.append(bad_pick)

                    except Exception as e:
                        logging.error(f"[OneShot] Retry Parse Error: {e}")
                        # Fallback: add original bad picks with warnings
                        for bp in picks_to_retry:
                            bp["warning"] = f"Semantic Flag: {bp.get('error_reason')}"
                            final_picks.append(bp)
                else:
                    # Retry failed, keep originals with warnings
                    for bp in picks_to_retry:
                        bp["warning"] = f"Semantic Flag: {bp.get('error_reason')}"
                        final_picks.append(bp)

            return final_picks

        except json.JSONDecodeError:
            logging.error(f"[OneShot] Invalid JSON returned: {response_str[:100]}...")
            return []

    except Exception as e:
        logging.error(f"[OneShot] Error: {e}")
        return []

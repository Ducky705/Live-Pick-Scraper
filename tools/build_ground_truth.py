import asyncio
import json
import logging
import os
import re
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.openrouter_client import openrouter_completion
from src.score_fetcher import fetch_scores_for_date

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GroundTruthBuilder")

INPUT_FILE = os.path.join(os.path.dirname(__file__), "../data/raw_test_candidates.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "../new_golden_set.json")

# High-Fidelity Prompt for Ground Truth Generation
ANALYST_PROMPT = """
You are a Senior Sports Analyst creating a Ground Truth dataset.
Analyze the following Telegram message containing betting picks.
Your goal is 100% precision.

MESSAGE TEXT:
{text}

MESSAGE DATE: {date}

INSTRUCTIONS:
1. Extract every valid sports betting pick.
2. Normalize the League (NBA, NFL, NCAAB, NHL, etc.).
3. Extract the exact Pick (Team/Player + Line/Prop).
4. Extract Odds (US format, e.g., -110). If missing, use null.
5. Extract Units. If missing, default to 1.0.
6. IGNORE promos, marketing, or general chat.

FORMAT:
Return a JSON object with a key "picks" containing a list of objects:
{{
  "picks": [
    {{
      "pick": "Team Name -Spread / Total / Player Prop",
      "league": "LeagueCode",
      "odds": -110,
      "units": 1.0,
      "type": "Spread/Moneyline/Total/Prop"
    }}
  ]
}}
"""


def independent_grade(pick: dict, score_data: dict) -> dict:
    """
    Independently calculates the grade based on score data.
    Returns { "grade": "WIN/LOSS/PUSH/VOID", "proof": "Score: X-Y, Line: Z" }
    """
    if score_data.get("type") == "multi_competitor":
        return {"grade": "UNSUPPORTED", "proof": "Multi-Competitor Event"}

    try:
        pick_text = pick["pick"].lower()

        # 1. Moneyline
        if "ml" in pick_text or "moneyline" in pick_text:
            if "winner1" not in score_data:
                return {"grade": "ERROR", "proof": "Missing winner data"}

            winner = (
                score_data["team1"]
                if score_data["winner1"]
                else (score_data["team2"] if score_data.get("winner2") else "None")
            )

            team_picked = None
            t1_name = score_data.get("team1", "").lower()
            t2_name = score_data.get("team2", "").lower()

            # Helper for partial match
            def is_match(team_full, text):
                if team_full in text:
                    return True
                parts = [w.lower() for w in team_full.split() if len(w) > 3]
                return any(w in text for w in parts)

            if is_match(t1_name, pick_text):
                team_picked = score_data["team1"]
            elif is_match(t2_name, pick_text):
                team_picked = score_data["team2"]

            if not team_picked:
                return {
                    "grade": "UNKNOWN",
                    "proof": f"Could not map team name. Pick: {pick_text} vs {t1_name}/{t2_name}",
                }

            grade = "WIN" if team_picked == winner else "LOSS"
            if winner == "None":
                grade = "PUSH"  # Draw/No Contest

            return {"grade": grade, "proof": f"Winner: {winner}, Picked: {team_picked}"}

        # 2. Spread (Simplified regex parsing for ground truth)
        # Look for the line number in the pick text
        line_match = re.search(r"([-+]\d+\.?\d*)", pick_text)
        if line_match:
            line = float(line_match.group(1))

            # Identify team
            t1_name = score_data.get("team1", "").lower()
            t2_name = score_data.get("team2", "").lower()

            # Helper for partial match
            def is_match(team_full, text):
                if team_full in text:
                    return True
                parts = [w.lower() for w in team_full.split() if len(w) > 3]
                return any(w in text for w in parts)

            is_team1 = is_match(t1_name, pick_text)
            is_team2 = is_match(t2_name, pick_text)

            if is_team1 == is_team2:  # Ambiguous or neither
                return {
                    "grade": "UNKNOWN",
                    "proof": f"Team mapping ambiguous: {pick_text} vs {t1_name}/{t2_name}",
                }

            s1 = float(score_data.get("score1") or 0)
            s2 = float(score_data.get("score2") or 0)

            score = s1 if is_team1 else s2
            opp_score = s2 if is_team1 else s1

            adjusted_score = score + line

            if adjusted_score > opp_score:
                grade = "WIN"
            elif adjusted_score < opp_score:
                grade = "LOSS"
            else:
                grade = "PUSH"

            return {"grade": grade, "proof": f"{score} ({line}) vs {opp_score}"}

        # 3. Total
        total_match = re.search(r"(o|over|u|under)\s*(\d+\.?\d*)", pick_text)
        if total_match:
            side = total_match.group(1)
            line = float(total_match.group(2))

            total_score = float(score_data.get("score1") or 0) + float(score_data.get("score2") or 0)

            if "o" in side:
                if total_score > line:
                    grade = "WIN"
                elif total_score < line:
                    grade = "LOSS"
                else:
                    grade = "PUSH"
            elif total_score < line:
                grade = "WIN"
            elif total_score > line:
                grade = "LOSS"
            else:
                grade = "PUSH"

            return {"grade": grade, "proof": f"Total: {total_score} vs {line}"}

        return {"grade": "UNSUPPORTED", "proof": "Complex Type"}

    except Exception as e:
        # Debugging aid
        missing = [k for k in ["team1", "winner1"] if k not in score_data]
        if missing and score_data.get("type") != "multi_competitor":
            return {"grade": "ERROR", "proof": f"Missing keys: {missing}"}
        return {"grade": "ERROR", "proof": str(e)}


async def build_dataset():
    if not os.path.exists(INPUT_FILE):
        logger.error(f"Input file not found: {INPUT_FILE}")
        return

    with open(INPUT_FILE, encoding="utf-8") as f:
        raw_data = json.load(f)

    logger.info(f"Loaded {len(raw_data)} raw messages.")

    verified_data = []

    # Process a subset or all
    for i, msg in enumerate(raw_data):
        if i >= 15:
            break  # Limit for initial build to save API costs/time

        logger.info(f"Processing Msg {i + 1}/{len(raw_data)} (ID: {msg['id']})")

        # 1. Parse
        prompt = ANALYST_PROMPT.format(text=msg["text"], date=msg["date"])
        try:
            # Use specific high-quality model
            response = openrouter_completion(prompt, model="google/gemini-2.0-flash-exp:free")
            parsed = json.loads(response)
            picks = parsed.get("picks", [])

            if not picks:
                logger.info("  No picks found by Analyst.")
                continue

            # 2. Verify against Live Scores
            msg_date_str = msg["date"].split()[0]  # YYYY-MM-DD
            scores = fetch_scores_for_date(msg_date_str)

            verified_picks = []

            for p in picks:
                # Find matching game
                matched_game = None

                # Smart matching logic
                for game in scores:
                    t1 = game.get("team1", "").lower()
                    t2 = game.get("team2", "").lower()

                    # Skip if names are empty (e.g. golf)
                    if not t1 or not t2:
                        continue

                    p_text = p["pick"].lower()

                    match_found = False
                    # 1. Full name match
                    if t1 in p_text or t2 in p_text:
                        match_found = True
                    # 2. Partial match (e.g. "Oilers" in "Edmonton Oilers")
                    else:
                        t1_parts = [w.lower() for w in t1.split() if len(w) > 3]
                        t2_parts = [w.lower() for w in t2.split() if len(w) > 3]
                        if any(w in p_text for w in t1_parts) or any(w in p_text for w in t2_parts):
                            match_found = True

                    if match_found:
                        matched_game = game
                        break

                grade_info = {"grade": "PENDING", "proof": "No game found"}

                if matched_game:
                    grade_info = independent_grade(p, matched_game)
                    logger.info(f"  [Verified] {p['pick']} -> {grade_info['grade']} ({grade_info['proof']})")
                else:
                    logger.warning(f"  [Unmatched] {p['pick']} (Date: {msg_date_str})")

                # Add verification data
                p["verified_grade"] = grade_info["grade"]
                p["verification_proof"] = grade_info["proof"]
                p["game_id"] = matched_game.get("id") if matched_game else None
                verified_picks.append(p)

            # Add to dataset
            new_entry = msg.copy()
            new_entry["expected_picks"] = verified_picks
            verified_data.append(new_entry)

        except Exception as e:
            logger.error(f"Error processing msg {msg['id']}: {e}")
            continue

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(verified_data, f, indent=2)

    logger.info(f"Ground Truth Built! Saved {len(verified_data)} verified cases to {OUTPUT_FILE}")


if __name__ == "__main__":
    # Ensure event loop for sync calls if needed
    asyncio.run(build_dataset())

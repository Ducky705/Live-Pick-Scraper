#!/usr/bin/env python3
"""
Golden Set Rapid Benchmark
==========================
Runs the AI parser against the golden set and evaluates accuracy.
Designed for rapid iteration on prompt/parser improvements.

Usage:
    python tools/run_golden_benchmark.py
    python tools/run_golden_benchmark.py --limit 10  # Test first 10 images
    python tools/run_golden_benchmark.py --verbose   # Show all errors
"""

import argparse
import base64
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.openrouter_client import openrouter_completion

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Model to benchmark
VISION_MODEL = "google/gemini-2.0-flash-exp:free"

# ============================================================================
# METRICS CLASSES
# ============================================================================


@dataclass
class FieldMetrics:
    """Tracks accuracy for a single field."""

    correct: int = 0
    total: int = 0
    errors: list = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total > 0 else 0.0

    def record(self, expected: any, actual: any, context: str = ""):
        self.total += 1
        if self._compare(expected, actual):
            self.correct += 1
        else:
            self.errors.append({"expected": expected, "actual": actual, "context": context})

    def _compare(self, expected: any, actual: any) -> bool:
        """Flexible comparison with normalization."""
        if expected is None and actual is None:
            return True
        if expected is None or actual is None:
            return False

        # Normalize strings
        if isinstance(expected, str) and isinstance(actual, str):
            return self._normalize(expected) == self._normalize(actual)

        # Numeric comparison with tolerance
        if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return abs(expected - actual) < 0.01

        return expected == actual

    def _normalize(self, s: str) -> str:
        """Normalize string for comparison."""
        return s.lower().strip().replace("  ", " ")


@dataclass
class EvaluationResult:
    """Aggregated evaluation results."""

    total_images: int = 0
    total_expected_picks: int = 0
    total_actual_picks: int = 0
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    # Field-level metrics
    league: FieldMetrics = field(default_factory=FieldMetrics)
    bet_type: FieldMetrics = field(default_factory=FieldMetrics)
    pick: FieldMetrics = field(default_factory=FieldMetrics)
    odds: FieldMetrics = field(default_factory=FieldMetrics)
    subject: FieldMetrics = field(default_factory=FieldMetrics)
    market: FieldMetrics = field(default_factory=FieldMetrics)
    line: FieldMetrics = field(default_factory=FieldMetrics)
    prop_side: FieldMetrics = field(default_factory=FieldMetrics)

    # Error tracking
    missed_picks: list = field(default_factory=list)
    extra_picks: list = field(default_factory=list)

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)


# ============================================================================
# PARSING PROMPT
# ============================================================================


def get_parsing_prompt():
    """Generate the parsing prompt for a single image."""
    return """
*** SYSTEM INSTRUCTION: SET TEMPERATURE TO 0 ***
*** OUTPUT FORMAT: RAW JSON ONLY. NO MARKDOWN. ***

You are an expert sports betting data parser. Analyze this betting slip image and extract ALL VALID BETTING PICKS.

### **CRITICAL RULE: PARLAY DETECTION (READ CAREFULLY!)**

**A PARLAY is a SINGLE BET combining multiple selections on ONE TICKET:**
- Look for ONE ticket/slip with MULTIPLE selections listed together
- Usually has ONE total "Apuesta Total" (Total Wager) and ONE "Ganancia Total" (Total Payout)
- Selections are connected/listed sequentially within the same box/card
- Combined odds shown for the whole ticket

**HOW TO IDENTIFY SEPARATE BETS:**
- Different ticket numbers or confirmation boxes
- Each has its OWN "Apuesta Total" / wager amount
- Separate "LAS VEGAS" or sportsbook headers between them
- Visual separation (different cards/boxes)

**IF MULTIPLE SELECTIONS ARE ON THE SAME TICKET → OUTPUT AS ONE PARLAY:**
- Type: "Parlay"  
- Combine ALL legs with " / " separator
- Example: "Dortmund ML / Hamburg Over 2.5 / Mainz Under 3.5"

### **SPANISH BETTING TERMS (CRITICAL!)**

| Spanish | English |
|---------|---------|
| Ambos equipos marcan | BTTS Yes |
| Ambos anotan | BTTS Yes |
| Más de X.X | Over X.X |
| Menos de X.X | Under X.X |
| Doble oportunidad | Double Chance |
| 1x2 | Moneyline (ML) |
| Línea de dinero | ML |
| Total córneres | Total Corners |
| Goles | Goals |
| Empate | Draw |
| Partido (sin prórrogas) | Match (Regular Time) |
| Apuesta Total | Total Wager |
| Ganancia Total | Total Payout |
| Pago Anticipado | Early Payout |

### **GERMAN BETTING TERMS**

| German | English |
|--------|---------|
| Beide Teams treffen | BTTS Yes |
| Über X.X | Over X.X |
| Unter X.X | Under X.X |
| Doppelte Chance | Double Chance |
| Sieg | ML (Win) |
| Ecken | Corners |

**ALWAYS OUTPUT IN ENGLISH FORMAT**

### **EXAMPLE: SPANISH 3-LEG PARLAY (ONE TICKET)**
Image shows ONE LAS VEGAS ticket with:
- Borussia Dortmund (1x2) @ -256
- Más de 2.5 - Hamburgo vs Leverkusen @ -141
- Menos de 3.5 - FSV Mainz vs Heidenheim @ -233
- Apuesta Total: $5,000 / Ganancia Total: $16,995

**OUTPUT 1 PARLAY (combined legs):**
{"picks": [
  {"lg": "Other", "ty": "Parlay", "p": "Borussia Dortmund ML / Hamburg vs Bayer Leverkusen Over 2.5 / FSV Mainz vs 1. FC Heidenheim 1846 Under 3.5", "od": 541, "u": 1.0, "sub": null, "mkt": null, "ln": null, "side": null}
]}

### **EXAMPLE: TWO SEPARATE SPANISH BETS (TWO TICKETS)**
Image shows TWO separate LAS VEGAS tickets:
- Ticket 1: Ambos equipos marcan - Hamburgo vs Leverkusen @ -164
- Ticket 2: Parlay with Double Chance + Corners

**OUTPUT 2 SEPARATE PICKS:**
{"picks": [
  {"lg": "Other", "ty": "Team Prop", "p": "Hamburg vs Bayer Leverkusen: BTTS Yes", "od": -164, "u": 1.0, "sub": "Hamburg vs Bayer Leverkusen", "mkt": "BTTS", "ln": null, "side": "Yes"},
  {"lg": "Other", "ty": "Parlay", "p": "Borussia Dortmund Double Chance / Borussia Dortmund vs Werder Bremen Total Corners Over 8.5", "od": -139, "u": 1.0, "sub": null, "mkt": null, "ln": null, "side": null}
]}

### **DOUBLE CHANCE FORMAT**
"Doble oportunidad: Team / Empate" means "Team or Draw" = "Team Double Chance"
Output as: "Team Double Chance"

### **CORNERS FORMAT**
"Total córneres - Más de 8.5" = "Total Corners Over 8.5"
Output as: "Team A vs Team B Total Corners Over 8.5"

### **ANTI-HALLUCINATION RULES**
1. Only extract ACTUAL BETTING PICKS with: Team/Player + Line/Market
2. DO NOT extract: Usernames, watermarks (@reypicks1), promotional text
3. If NO valid betting picks visible, return: {"picks": []}
4. DO NOT split parlay legs into separate picks if they're on the same ticket!

### **OUTPUT FORMAT**
Return JSON with "picks" array. Use SHORT KEYS:
- "lg": league (NBA, NFL, NHL, MLB, NCAAF, NCAAB, TENNIS, UFC, Other)
- "ty": type (Moneyline, Spread, Total, Player Prop, Team Prop, Period, Parlay)
- "p": pick text in English (NO odds in this field!)
- "od": odds (integer or null if not visible)
- "u": units (float, default 1.0)
- "sub": subject (team/player, null for parlays)
- "mkt": market (null for parlays)
- "ln": line (null for ML/parlays)
- "side": Over/Under or null

**COUNT THE TICKET BOXES FIRST. Each separate ticket = separate pick. Multiple selections on ONE ticket = ONE parlay.**

If NO valid picks found: {"picks": []}
"""


# ============================================================================
# MULTI-PROVIDER PARALLEL PARSER
# ============================================================================


def call_mistral_vision(prompt: str, b64_img: str) -> str:
    """Call Mistral Pixtral for vision parsing."""
    try:
        from src.mistral_client import PIXTRAL_LARGE, mistral_completion

        response = mistral_completion(prompt, model=PIXTRAL_LARGE, image_input=b64_img, timeout=90)
        return response
    except Exception as e:
        logging.error(f"[Mistral] Error: {e}")
        return None


def call_gemini_vision(prompt: str, b64_img: str) -> str:
    """Call Gemini for vision parsing."""
    try:
        from src.gemini_client import gemini_vision_completion

        response = gemini_vision_completion(prompt, b64_img)
        return response
    except Exception as e:
        logging.error(f"[Gemini] Error: {e}")
        return None


def call_groq_vision(prompt: str, b64_img: str) -> str:
    """Call Groq Llama Vision for parsing."""
    try:
        from src.groq_client import groq_vision_completion

        response = groq_vision_completion(prompt, b64_img)
        return response
    except Exception as e:
        logging.error(f"[Groq] Error: {e}")
        return None


def call_openrouter_vision(prompt: str, b64_img: str) -> str:
    """Call OpenRouter (with fallback models) for vision parsing."""
    try:
        response = openrouter_completion(prompt, model=VISION_MODEL, images=[b64_img], timeout=120, max_cycles=3)
        return response
    except Exception as e:
        logging.error(f"[OpenRouter] Error: {e}")
        return None


def parse_response(response: str) -> list[dict[str, Any]]:
    """Parse AI response into picks list."""
    if not response:
        return []

    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.strip()

        data = json.loads(cleaned)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return data.get("picks", [])
        return []
    except json.JSONDecodeError:
        return []


# Spanish to English translations for betting terms
SPANISH_TRANSLATIONS = {
    # Betting terms
    "ambos equipos marcan": "BTTS Yes",
    "ambos anotan": "BTTS Yes",
    "más de": "Over",
    "menos de": "Under",
    "doble oportunidad": "Double Chance",
    "línea de dinero": "ML",
    "linea de dinero": "ML",
    "total córners": "Total Corners",
    "total corners": "Total Corners",
    "partido": "Match",
    "sin prórrogas": "",
    "sin prorrogas": "",
    "empate": "Draw",
    # Common teams
    "hamburgo": "Hamburg",
}


def normalize_pick_text(pick_text: str) -> str:
    """Normalize pick text - translate Spanish, standardize format."""
    if not pick_text:
        return pick_text

    result = pick_text

    # Apply Spanish translations (case-insensitive)
    lower_result = result.lower()
    for spanish, english in SPANISH_TRANSLATIONS.items():
        if spanish in lower_result:
            # Find and replace preserving some case
            result = re.sub(re.escape(spanish), english, result, flags=re.IGNORECASE)

    # Standardize betting terms
    result = re.sub(r"\bmoney\s*line\b", "ML", result, flags=re.IGNORECASE)
    result = re.sub(r"\bmoneyline\b", "ML", result, flags=re.IGNORECASE)
    result = re.sub(r"\brushing\s*yards?\b", "RushYds", result, flags=re.IGNORECASE)
    result = re.sub(r"\breceiving\s*yards?\b", "RecYds", result, flags=re.IGNORECASE)
    result = re.sub(r"\bpassing\s*yards?\b", "PassYds", result, flags=re.IGNORECASE)
    result = re.sub(r"\bpassing\s*tds?\b", "PassTD", result, flags=re.IGNORECASE)
    result = re.sub(r"\bpoints?\b", "Pts", result, flags=re.IGNORECASE)
    result = re.sub(r"\brebounds?\b", "Reb", result, flags=re.IGNORECASE)
    result = re.sub(r"\bassists?\b", "Ast", result, flags=re.IGNORECASE)

    # Clean up whitespace
    result = " ".join(result.split())

    return result


def merge_potential_parlays(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Detect and merge split parlay legs into a single parlay pick.

    Key patterns that indicate AI incorrectly split a parlay:
    1. Multiple picks sharing the SAME unusual odds (not -110, -115, etc.)
    2. Many picks (8+) with null odds
    3. 2-4 picks that are clearly legs (same sport/league, sequential)
    4. Picks with very unusual odds (like -256, -141, -233) that sum to parlay-like odds
    """
    if len(picks) < 2:
        return picks

    # Check if any picks are already formatted as parlays (have " / " in text)
    parlay_formatted = [p for p in picks if " / " in (p.get("p") or "")]

    # If some are already parlays and some aren't, return as-is
    if parlay_formatted and len(parlay_formatted) != len(picks):
        return picks

    # Group picks by odds value
    by_odds = {}
    null_odds = []
    for p in picks:
        od = p.get("od")
        if od is None:
            null_odds.append(p)
        else:
            if od not in by_odds:
                by_odds[od] = []
            by_odds[od].append(p)

    # PATTERN 1: Multiple picks (2+) with SAME unusual odds = split parlay
    standard_odds = {-110, -115, -105, -120, -125, 100, -100, 110, 105, 115, 120}

    for od, group in by_odds.items():
        is_unusual = od not in standard_odds and abs(od) >= 100
        if is_unusual and len(group) >= 2:
            legs = [g.get("p", "") for g in group]
            merged_parlay = {
                "lg": "Other",
                "ty": "Parlay",
                "p": " / ".join(legs),
                "od": od,
                "u": group[0].get("u", 1.0),
                "sub": None,
                "mkt": None,
                "ln": None,
                "side": None,
            }
            others = [p for p in picks if p not in group]
            return [merged_parlay] + others

    # PATTERN 2: Many picks (8+) with null odds = mega-parlay was split
    if len(null_odds) >= 8:
        legs = [p.get("p", "") for p in null_odds]
        merged_parlay = {
            "lg": "Other",
            "ty": "Parlay",
            "p": " / ".join(legs),
            "od": None,
            "u": null_odds[0].get("u", 1.0) if null_odds else 1.0,
            "sub": None,
            "mkt": None,
            "ln": None,
            "side": None,
        }
        others = [p for p in picks if p.get("od") is not None]
        return [merged_parlay] + others

    # PATTERN 3: Many picks (10+) total = definitely split parlay
    if len(picks) >= 10:
        legs = [p.get("p", "") for p in picks]
        combined_odds = None
        for p in picks:
            od = p.get("od")
            if od is not None and abs(od) >= 300:
                combined_odds = od
                break

        merged_parlay = {
            "lg": "Other",
            "ty": "Parlay",
            "p": " / ".join(legs),
            "od": combined_odds,
            "u": picks[0].get("u", 1.0),
            "sub": None,
            "mkt": None,
            "ln": None,
            "side": None,
        }
        return [merged_parlay]

    # PATTERN 4: 3 picks with all unusual odds (not standard) = likely 3-leg parlay
    # This catches the case where AI extracted individual leg odds instead of combined
    if len(picks) == 3:
        all_unusual = True
        for p in picks:
            od = p.get("od")
            if od is None or od in standard_odds:
                all_unusual = False
                break

        if all_unusual:
            # Check if all picks are same league (indicates same parlay)
            leagues = set(p.get("lg", "Other") for p in picks)
            if len(leagues) == 1 or "Other" in leagues:
                legs = [p.get("p", "") for p in picks]
                # Calculate approximate combined odds (rough estimate)
                combined = None  # We don't know the true combined odds
                merged_parlay = {
                    "lg": "Other",
                    "ty": "Parlay",
                    "p": " / ".join(legs),
                    "od": combined,
                    "u": picks[0].get("u", 1.0),
                    "sub": None,
                    "mkt": None,
                    "ln": None,
                    "side": None,
                }
                return [merged_parlay]

    # Default: return picks unchanged
    return picks


def post_process_picks(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Post-process picks to normalize format and merge split parlays."""
    if not picks:
        return picks

    processed = []

    for pick in picks:
        # Normalize pick text
        if "p" in pick:
            pick["p"] = normalize_pick_text(pick["p"])

        # Skip picks that are clearly invalid after normalization
        p_text = pick.get("p", "").strip()
        if not p_text or len(p_text) < 3:
            continue

        # Skip if it's just punctuation or Spanish fragments
        if p_text in ["-", "/", "Yes", "No", "Over", "Under"]:
            continue

        processed.append(pick)

    # Apply merging strategy
    return merge_potential_parlays(processed)


def parse_image(image_path: str, use_gemini_direct: bool = False, use_parallel: bool = True) -> list[dict[str, Any]]:
    """
    Parse a single image using AI model(s).

    If use_parallel=True, races multiple providers in parallel and returns
    the BEST result (most picks found). This avoids rate limit bottlenecks
    and improves accuracy by picking the most complete response.
    """
    if not os.path.exists(image_path):
        logging.error(f"Image not found: {image_path}")
        return []

    try:
        # Encode image
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        prompt = get_parsing_prompt()

        if use_parallel:
            # PARALLEL MULTI-PROVIDER: Run all providers, pick best result
            from concurrent.futures import ThreadPoolExecutor, wait

            providers = [
                ("OpenRouter", lambda: call_openrouter_vision(prompt, b64_img)),
                ("Mistral", lambda: call_mistral_vision(prompt, b64_img)),
                # ("Groq", lambda: call_groq_vision(prompt, b64_img)),  # Decommissioned
                ("Gemini", lambda: call_gemini_vision(prompt, b64_img)),
            ]

            results = []  # Collect (provider, picks) tuples

            with ThreadPoolExecutor(max_workers=len(providers)) as executor:
                future_to_provider = {executor.submit(fn): name for name, fn in providers}

                # Wait for all to complete (with timeout)
                done, pending = wait(future_to_provider.keys(), timeout=90)

                # Cancel any still running
                for f in pending:
                    f.cancel()

                # Collect successful results
                for future in done:
                    provider_name = future_to_provider[future]
                    try:
                        response = future.result()
                        if response:
                            parsed = parse_response(response)
                            if parsed:
                                processed = post_process_picks(parsed)
                                results.append((provider_name, processed))
                                logging.info(f"[{provider_name}] Got {len(processed)} picks")
                    except Exception as e:
                        logging.error(f"[{provider_name}] Failed: {e}")

            # Pick the BEST result (most picks, as long as not excessive)
            if results:
                # Sort by number of picks, prefer 1-10 range
                def score_result(r):
                    name, picks = r
                    count = len(picks)
                    # Prefer results with reasonable pick counts (1-10)
                    if 1 <= count <= 10:
                        return count + 100  # Bonus for reasonable range
                    elif count > 10:
                        return count  # Still valid but lower priority
                    return 0  # No picks = worst

                results.sort(key=score_result, reverse=True)
                best_provider, best_picks = results[0]
                logging.info(f"[BEST] Using {best_provider} with {len(best_picks)} picks")
                return best_picks

            return []

        # Single provider mode (legacy)
        if use_gemini_direct:
            from src.gemini_client import gemini_vision_completion

            response = gemini_vision_completion(prompt, b64_img)
        else:
            response = openrouter_completion(prompt, model=VISION_MODEL, images=[b64_img], timeout=120, max_cycles=5)

        if not response:
            return []

        picks = parse_response(response)
        return post_process_picks(picks)

    except json.JSONDecodeError as e:
        logging.error(f"JSON parse error for {os.path.basename(image_path)}: {e}")
        return []
    except Exception as e:
        logging.error(f"Error parsing {os.path.basename(image_path)}: {e}")
        return []


# ============================================================================
# MATCHING & EVALUATION
# ============================================================================


def normalize_pick(pick: str) -> str:
    """Normalize pick string for matching."""
    if not pick:
        return ""
    s = pick.lower().strip()
    s = " ".join(s.split())
    # Common abbreviations - standardize both directions
    s = s.replace("los angeles ", "la ")
    s = s.replace("new york ", "ny ")
    s = s.replace("golden state ", "gs ")
    # Betting term normalization
    s = s.replace("money line", "ml")
    s = s.replace("moneyline", "ml")
    s = s.replace("rushing yards", "rushyds")
    s = s.replace("receiving yards", "recyds")
    s = s.replace("passing yards", "passyds")
    s = s.replace("passing td", "passtd")
    s = s.replace("passing tds", "passtd")
    s = s.replace("40+", "over 39.5")
    s = s.replace("25+", "over 24.5")
    # Remove common separators
    s = s.replace(": ", " ")
    return s


def similarity(s1: str, s2: str) -> float:
    """Calculate string similarity (0-1)."""
    return SequenceMatcher(None, normalize_pick(s1), normalize_pick(s2)).ratio()


def parlay_leg_similarity(expected_pick: str, actual_pick: str) -> float:
    """
    Calculate similarity for parlays based on matching legs.

    Instead of comparing the full string, we split by " / " and count
    how many legs match between expected and actual.

    Returns a score from 0-1 based on:
    - Percentage of expected legs found in actual
    - Bonus for having similar number of legs
    """
    if not expected_pick or not actual_pick:
        return 0.0

    # Split into legs
    exp_legs = [normalize_pick(leg.strip()) for leg in expected_pick.split(" / ")]
    act_legs = [normalize_pick(leg.strip()) for leg in actual_pick.split(" / ")]

    # If neither is a parlay (single leg), use normal similarity
    if len(exp_legs) == 1 and len(act_legs) == 1:
        return similarity(expected_pick, actual_pick)

    # Count how many expected legs are found in actual
    matched_legs = 0
    used_actual = set()

    for exp_leg in exp_legs:
        best_match_score = 0
        best_match_idx = -1

        for i, act_leg in enumerate(act_legs):
            if i in used_actual:
                continue

            # Calculate similarity between individual legs
            leg_sim = SequenceMatcher(None, exp_leg, act_leg).ratio()
            if leg_sim > best_match_score and leg_sim >= 0.6:  # Threshold for leg match
                best_match_score = leg_sim
                best_match_idx = i

        if best_match_idx >= 0:
            matched_legs += best_match_score  # Weighted match
            used_actual.add(best_match_idx)

    if len(exp_legs) == 0:
        return 0.0

    # Calculate score: percentage of expected legs matched
    leg_match_ratio = matched_legs / len(exp_legs)

    # Penalty for very different number of legs (hallucinating extra legs or missing many)
    leg_count_ratio = min(len(exp_legs), len(act_legs)) / max(len(exp_legs), len(act_legs))

    # Final score: weighted combination
    # - 80% weight on leg match ratio
    # - 20% weight on having similar number of legs
    final_score = 0.8 * leg_match_ratio + 0.2 * leg_count_ratio

    return final_score


def match_picks(expected: list[dict], actual: list[dict], threshold: float = 0.65) -> tuple:
    """Match actual picks to expected picks using parlay-aware matching."""
    matched = []
    unmatched_expected = list(expected)
    unmatched_actual = list(actual)

    for exp in expected:
        exp_pick = exp.get("pick", "")
        exp_type = exp.get("type", "")
        best_match = None
        best_score = 0

        for act in unmatched_actual:
            act_pick = act.get("p") or act.get("pick", "")
            act_type = act.get("ty") or act.get("type", "")

            # Use parlay-aware matching for parlays (leg-by-leg comparison)
            is_exp_parlay = exp_type == "Parlay" or " / " in exp_pick
            is_act_parlay = act_type == "Parlay" or " / " in act_pick

            if is_exp_parlay or is_act_parlay:
                # Use leg-based similarity for parlays
                score = parlay_leg_similarity(exp_pick, act_pick)
            else:
                # Use standard string similarity for non-parlays
                score = similarity(exp_pick, act_pick)

            # Bonus for matching league/type
            if exp.get("league") == (act.get("lg") or act.get("league")):
                score += 0.05
            if exp_type == act_type:
                score += 0.05

            if score > best_score:
                best_score = score
                best_match = act

        if best_match and best_score >= threshold:
            matched.append((exp, best_match))
            unmatched_expected.remove(exp)
            unmatched_actual.remove(best_match)

    return matched, unmatched_expected, unmatched_actual


def evaluate_image(expected_picks: list[dict], actual_picks: list[dict], result: EvaluationResult, image_path: str):
    """Evaluate parser output for a single image."""
    result.total_images += 1
    result.total_expected_picks += len(expected_picks)
    result.total_actual_picks += len(actual_picks)

    matched, missed, extra = match_picks(expected_picks, actual_picks)

    result.true_positives += len(matched)
    result.false_negatives += len(missed)
    result.false_positives += len(extra)

    # Track missed/extra
    for m in missed:
        result.missed_picks.append({"image": os.path.basename(image_path), "pick": m.get("pick")})

    for e in extra:
        result.extra_picks.append({"image": os.path.basename(image_path), "pick": e.get("p") or e.get("pick")})

    # Field accuracy for matched picks
    for exp, act in matched:
        ctx = exp.get("pick", "")[:50]

        result.league.record(exp.get("league"), act.get("lg") or act.get("league"), ctx)
        result.bet_type.record(exp.get("type"), act.get("ty") or act.get("type"), ctx)
        result.pick.record(exp.get("pick"), act.get("p") or act.get("pick"), ctx)
        result.odds.record(exp.get("odds"), act.get("od") or act.get("odds"), ctx)
        result.subject.record(exp.get("subject"), act.get("sub") or act.get("subject"), ctx)
        result.market.record(exp.get("market"), act.get("mkt") or act.get("market"), ctx)
        result.line.record(exp.get("line"), act.get("ln") or act.get("line"), ctx)
        result.prop_side.record(exp.get("prop_side"), act.get("side") or act.get("prop_side"), ctx)


# ============================================================================
# REPORTING
# ============================================================================


def print_report(result: EvaluationResult, verbose: bool = False):
    """Print evaluation report."""
    print("\n" + "=" * 70)
    print("GOLDEN SET BENCHMARK REPORT")
    print("=" * 70)

    print(f"\n{'DETECTION METRICS':-^70}")
    print(f"  Images evaluated:     {result.total_images}")
    print(f"  Expected picks:       {result.total_expected_picks}")
    print(f"  Returned picks:       {result.total_actual_picks}")
    print(f"  Matched (TP):         {result.true_positives}")
    print(f"  Missed (FN):          {result.false_negatives}")
    print(f"  Extra (FP):           {result.false_positives}")
    print()
    print(f"  Precision:            {result.precision:.1%}")
    print(f"  Recall:               {result.recall:.1%}")
    print(f"  F1 Score:             {result.f1:.1%}")

    print(f"\n{'FIELD ACCURACY (on matched picks)':-^70}")
    fields = [
        ("League", result.league),
        ("Type", result.bet_type),
        ("Pick", result.pick),
        ("Odds", result.odds),
        ("Subject", result.subject),
        ("Market", result.market),
        ("Line", result.line),
        ("Prop Side", result.prop_side),
    ]

    for name, metrics in fields:
        if metrics.total > 0:
            bar = "#" * int(metrics.accuracy * 20)
            print(f"  {name:<12} {metrics.accuracy:>6.1%} ({metrics.correct}/{metrics.total}) [{bar:<20}]")

    # Show missed picks
    if result.missed_picks:
        print(f"\n{'MISSED PICKS (False Negatives)':-^70}")
        for i, m in enumerate(result.missed_picks[:10]):
            print(f"  [{m['image']}] {m['pick']}")
        if len(result.missed_picks) > 10:
            print(f"  ... and {len(result.missed_picks) - 10} more")

    # Show extra picks (hallucinations)
    if result.extra_picks:
        print(f"\n{'EXTRA PICKS (False Positives)':-^70}")
        for i, e in enumerate(result.extra_picks[:10]):
            print(f"  [{e['image']}] {e['pick']}")
        if len(result.extra_picks) > 10:
            print(f"  ... and {len(result.extra_picks) - 10} more")

    # Show field errors
    if verbose:
        print(f"\n{'FIELD ERRORS (sample)':-^70}")
        for name, metrics in fields:
            if metrics.errors:
                print(f"\n{name}:")
                for err in metrics.errors[:3]:
                    print(f"  Expected: {err['expected']}")
                    print(f"  Actual:   {err['actual']}")
                    print(f"  Context:  {err['context']}")
                    print()


# ============================================================================
# MAIN
# ============================================================================


def load_golden_set(path: Path) -> list[dict]:
    """Load golden set from JSONL file."""
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def main():
    parser = argparse.ArgumentParser(description="Run AI parser benchmark against golden set")
    parser.add_argument(
        "--golden-set",
        type=Path,
        default=Path(__file__).parent.parent / "golden_set" / "golden_set.jsonl",
        help="Path to golden_set.jsonl",
    )
    parser.add_argument("--limit", type=int, help="Limit number of images to test")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed errors")
    parser.add_argument(
        "--parallel", action="store_true", help="Use parallel multi-provider parsing (faster, avoids rate limits)"
    )
    parser.add_argument(
        "--delay", type=float, default=3.0, help="Delay between requests in seconds (ignored if --parallel)"
    )
    parser.add_argument("--output", "-o", type=Path, help="Save JSON report to file")
    args = parser.parse_args()

    if not args.golden_set.exists():
        print(f"Error: Golden set file not found: {args.golden_set}")
        sys.exit(1)

    # Load golden set
    golden_items = load_golden_set(args.golden_set)
    print(f"Loaded {len(golden_items)} items from golden set")

    if args.limit:
        golden_items = golden_items[: args.limit]
        print(f"Limited to {len(golden_items)} items")

    # Filter to only items with expected picks
    items_with_picks = [item for item in golden_items if item.get("expected_picks")]
    items_no_picks = [item for item in golden_items if not item.get("expected_picks")]

    print(f"Items with picks: {len(items_with_picks)}")
    print(f"Items without picks (should return empty): {len(items_no_picks)}")

    # Run parser on all images
    mode = "PARALLEL (multi-provider)" if args.parallel else f"sequential with {args.delay}s delay"
    print(f"\nRunning parser on {len(golden_items)} images ({mode})...")
    start_time = time.time()

    predictions = {}

    for i, item in enumerate(golden_items):
        image_path = item.get("image_path", "")
        picks = parse_image(image_path, use_parallel=args.parallel)
        predictions[image_path] = picks

        # Progress
        elapsed = time.time() - start_time
        print(f"  [{i + 1}/{len(golden_items)}] {os.path.basename(image_path)}: {len(picks)} picks ({elapsed:.1f}s)")

        # Delay between requests only if not parallel mode
        if not args.parallel and i < len(golden_items) - 1:
            time.sleep(args.delay)

    elapsed = time.time() - start_time
    print(f"\nParsing complete in {elapsed:.1f}s ({elapsed / len(golden_items):.2f}s per image)")

    # Evaluate
    result = EvaluationResult()

    for item in golden_items:
        image_path = item.get("image_path", "")
        expected = item.get("expected_picks", [])
        actual = predictions.get(image_path, [])

        evaluate_image(expected, actual, result, image_path)

    # Print report
    print_report(result, verbose=args.verbose)

    # Save JSON report
    if args.output:
        report = {
            "total_images": result.total_images,
            "total_expected": result.total_expected_picks,
            "total_actual": result.total_actual_picks,
            "precision": result.precision,
            "recall": result.recall,
            "f1": result.f1,
            "field_accuracy": {
                "league": result.league.accuracy,
                "type": result.bet_type.accuracy,
                "pick": result.pick.accuracy,
                "odds": result.odds.accuracy,
                "subject": result.subject.accuracy,
                "market": result.market.accuracy,
                "line": result.line.accuracy,
                "prop_side": result.prop_side.accuracy,
            },
            "missed_picks": result.missed_picks,
            "extra_picks": result.extra_picks,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved to: {args.output}")

    # Return exit code based on F1
    if result.f1 < 0.7:
        print("\n[FAIL] F1 score below 70% threshold")
        return 1
    elif result.f1 < 0.85:
        print("\n[WARN] F1 score below 85% target")
        return 0
    else:
        print("\n[PASS] F1 score meets target!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

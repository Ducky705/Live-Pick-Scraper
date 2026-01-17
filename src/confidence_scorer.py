from src.models import BetPick
import re

class ConfidenceScorer:
    @staticmethod
    def calculate_score(pick: BetPick) -> dict:
        """
        Calculates a confidence score (0-100) for a pick and identifies specific issues.
        Returns: { "score": float, "issues": List[str] }
        """
        score = 100.0
        issues = []

        # CRITICAL FAILURES (Heavy Penalties)
        if not pick.pick or pick.pick.lower() in ["unknown", "n/a", "none", ""]:
            score -= 60
            issues.append("missing_pick_text")
        
        # KEY METADATA CHECKS
        if pick.league in ["Other", "Unknown", None, ""]:
            score -= 15
            issues.append("missing_league")
            
        if pick.type in ["Unknown", None, ""]:
            score -= 10
            issues.append("missing_bet_type")
            
        if pick.capper_name in ["Unknown", "N/A", None, ""]:
            score -= 10
            issues.append("missing_capper")

        # ODDS INTEGRITY
        # If it's a bet that typically needs odds (ML, Spread, Prop) but has none
        needs_odds = pick.type not in ["Futures", "Parlay"] 
        if needs_odds and (pick.odds is None or pick.odds == ""):
            score -= 15
            issues.append("missing_odds")

        # CONTENT QUALITY CHECKS
        if pick.pick:
            # Detect short nonsense picks
            if len(pick.pick) < 3:
                score -= 30
                issues.append("pick_too_short")
            
            # Detect raw OCR noise (too many special chars)
            if len(re.findall(r'[^a-zA-Z0-9\s\.\-\+]', pick.pick)) > 3:
                score -= 20
                issues.append("noisy_text")

        # LOGIC CHECKS
        if pick.warning:
            score -= 20
            issues.append(f"warning_{pick.warning.lower().replace(' ', '_')}")

        # CHEM/PROP CHECKS (If granularity attempted)
        if pick.subject or pick.market: # Check if granular fields exist
            if not pick.subject or not pick.market:
                score -= 15
                issues.append("incomplete_prop_data")

        return {
            "score": max(0.0, score),
            "issues": issues,
            "needs_verification": score < 85.0
        }

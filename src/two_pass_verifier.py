import logging
import re
from typing import Any

from src.semantic_validator import SemanticValidator


class TwoPassVerifier:
    """
    Handles verification of OCR and Parsing results.
    If confidence is low, it suggests a second pass with a stronger model.
    """

    # High-performance models for the second pass
    # Using the specific Chimera model requested for robust parsing
    STRONG_TEXT_MODEL = "tngtech/deepseek-r1t2-chimera:free"

    # Vision Model for Retry
    # 'google/gemini-2.0-pro-exp-02-05:free' is not currently available.
    # We fallback to the reliable Flash model, but the retry logic will use a boosted prompt.
    STRONG_VISION_MODEL = "google/gemini-2.0-flash-exp:free"

    @staticmethod
    def verify_ocr_result(text: str) -> bool:
        """
        Verifies if the OCR result looks valid and sufficient.
        Returns True if confident, False if verification fails (needs retry).
        """
        if not text:
            return False

        # Check for error messages from the model/system
        if text.startswith("[Error") or "AI returned invalid JSON" in text:
            return False

        # Check for extremely short output (likely failed extraction)
        # Increased threshold to 40 chars (betting slips usually have more)
        if len(text.strip()) < 40:
            return False

        # Check for "I cannot read this" type responses
        failure_phrases = [
            "cannot read",
            "no text found",
            "image is blurry",
            "unable to extract",
            "I can't see",
            "text is too small",
            "I am sorry",
            "I'm sorry",
            "cannot transcribe",
        ]
        text_lower = text.lower()
        for phrase in failure_phrases:
            if phrase in text_lower:
                return False

        # KEYWORD CHECK: A valid betting slip usually has numbers/odds
        # If no numbers found, it's likely a failure
        if not re.search(r"\d", text):
            return False

        return True

    @staticmethod
    def verify_parsing_result(picks: list[dict[str, Any]]) -> bool:
        """
        Verifies if the parsed picks contain sufficient information.
        Returns True if confident, False if verification fails (needs retry).
        """
        if not picks:
            return False

        # If any pick is significantly "Unknown", trigger retry
        unknown_count = 0
        total_picks = len(picks)

        # New: Semantic Validation Check
        semantic_issues = 0

        for pick in picks:
            # Critical fields missing
            capper = pick.get("capper_name", "Unknown")
            league = pick.get("league", "Unknown")
            pick_val = pick.get("pick", "")

            # Check for "Unknown" or empty
            is_bad_capper = capper in ["Unknown", "N/A", None, ""]
            is_bad_league = league in ["Unknown", "Other", None, ""]
            is_bad_pick = not pick_val or pick_val == "Unknown"

            if is_bad_capper or is_bad_league or is_bad_pick:
                unknown_count += 1

            # Check semantic validity
            is_valid, reason = SemanticValidator.validate(pick)
            if not is_valid:
                semantic_issues += 1
                logging.warning(f"[TwoPassVerifier] Semantic Issue: {reason} in {pick_val}")

        # Threshold: If > 30% of picks are bad, fail.
        if total_picks == 0:
            return False

        if (unknown_count / total_picks) > 0.3:
            logging.info(
                f"[TwoPassVerifier] Low confidence parsing: {unknown_count}/{total_picks} picks contain Unknown fields."
            )
            return False

        # If significant semantic issues found (> 20%), consider it a failure
        if (semantic_issues / total_picks) > 0.2:
            logging.info(
                f"[TwoPassVerifier] Low confidence parsing: {semantic_issues}/{total_picks} picks have semantic errors."
            )
            return False

        return True

    @staticmethod
    def get_strong_vision_model() -> str:
        return TwoPassVerifier.STRONG_VISION_MODEL

    @staticmethod
    def get_strong_text_model() -> str:
        return TwoPassVerifier.STRONG_TEXT_MODEL

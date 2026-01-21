# src/multi_capper_verifier.py
"""
Multi-Capper Verifier: Validates that picks from multi-capper posts are properly separated.

Problem:
- A single post may contain picks from multiple cappers
- AI might merge them into one capper name or miss some entirely
- No validation to detect this issue

Solution:
- Analyze parsed picks for proper capper separation
- Cross-reference with album correlation data
- Flag posts where capper attribution looks wrong
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set
from collections import Counter


@dataclass
class CapperVerificationResult:
    """Result of multi-capper verification."""
    is_valid: bool
    expected_cappers: List[str]
    actual_cappers: List[str]
    missing_cappers: List[str]
    merged_cappers: List[str]  # Comma-separated names that should be separate
    confidence: float
    needs_reparse: bool
    reason: str


class MultiCapperVerifier:
    """
    Verifies that picks from multi-capper posts are properly attributed.
    
    Detection signals:
    1. Comma-separated capper names (should be split)
    2. OCR block count vs unique capper count mismatch
    3. Known patterns of merged names
    """
    
    # Patterns that indicate incorrectly merged names
    MERGED_NAME_PATTERNS = [
        r'^.+,\s*.+$',           # "Capper1, Capper2"
        r'^.+\s+and\s+.+$',      # "Capper1 and Capper2"
        r'^.+\s*/\s*.+$',        # "Capper1 / Capper2"
        r'^.+\s+&\s+.+$',        # "Capper1 & Capper2"
    ]
    
    @classmethod
    def verify_picks(
        cls,
        picks: List[Dict[str, Any]],
        expected_cappers: Optional[List[str]] = None,
        ocr_block_count: int = 1,
        message_id: Optional[int] = None
    ) -> CapperVerificationResult:
        """
        Verify that picks have proper capper attribution.
        
        Args:
            picks: List of parsed picks for a single message
            expected_cappers: Optional list of expected capper names (from album correlation)
            ocr_block_count: Number of OCR blocks (images) in the message
            message_id: Optional message ID for logging
            
        Returns:
            CapperVerificationResult
        """
        if not picks:
            return cls._empty_result()
        
        # Extract capper names from picks
        actual_cappers = []
        merged_cappers = []
        
        for pick in picks:
            capper_name = pick.get('capper_name', pick.get('cn', 'Unknown'))
            if capper_name and capper_name not in ['Unknown', 'N/A', '']:
                actual_cappers.append(capper_name)
                
                # Check if this looks like a merged name
                if cls._is_merged_name(capper_name):
                    merged_cappers.append(capper_name)
        
        unique_cappers = list(set(actual_cappers))
        
        # Scenario 1: Check for merged names
        if merged_cappers:
            return CapperVerificationResult(
                is_valid=False,
                expected_cappers=expected_cappers or [],
                actual_cappers=unique_cappers,
                missing_cappers=[],
                merged_cappers=merged_cappers,
                confidence=0.9,
                needs_reparse=True,
                reason=f"Merged capper names detected: {merged_cappers}"
            )
        
        # Scenario 2: Expected cappers provided (from album correlation)
        if expected_cappers:
            return cls._verify_against_expected(
                unique_cappers, expected_cappers, message_id
            )
        
        # Scenario 3: Multiple OCR blocks but only one capper
        if ocr_block_count > 1 and len(unique_cappers) <= 1:
            return CapperVerificationResult(
                is_valid=False,
                expected_cappers=[],
                actual_cappers=unique_cappers,
                missing_cappers=[],
                merged_cappers=[],
                confidence=0.6,
                needs_reparse=True,
                reason=f"Multiple images ({ocr_block_count}) but only {len(unique_cappers)} unique capper(s)"
            )
        
        # Looks OK
        return CapperVerificationResult(
            is_valid=True,
            expected_cappers=expected_cappers or [],
            actual_cappers=unique_cappers,
            missing_cappers=[],
            merged_cappers=[],
            confidence=0.8,
            needs_reparse=False,
            reason=f"Capper attribution looks correct: {len(unique_cappers)} unique capper(s)"
        )
    
    @classmethod
    def _is_merged_name(cls, name: str) -> bool:
        """Check if a capper name looks like multiple names merged together."""
        for pattern in cls.MERGED_NAME_PATTERNS:
            if re.match(pattern, name, re.IGNORECASE):
                return True
        
        # Also check for suspiciously long names with multiple capital letters
        # e.g., "KingCapBetMasterPropKing"
        capital_count = sum(1 for c in name if c.isupper())
        if capital_count > 3 and len(name) > 20:
            # Might be concatenated names
            return True
        
        return False
    
    @classmethod
    def _verify_against_expected(
        cls,
        actual: List[str],
        expected: List[str],
        message_id: Optional[int]
    ) -> CapperVerificationResult:
        """Compare actual cappers against expected from album correlation."""
        
        # Normalize names for comparison
        actual_normalized = set(cls._normalize_name(n) for n in actual)
        expected_normalized = set(cls._normalize_name(n) for n in expected)
        
        # Find missing
        missing = []
        for exp in expected:
            exp_norm = cls._normalize_name(exp)
            if exp_norm not in actual_normalized:
                missing.append(exp)
        
        # Calculate match ratio
        if expected_normalized:
            matched = actual_normalized.intersection(expected_normalized)
            match_ratio = len(matched) / len(expected_normalized)
        else:
            match_ratio = 0.5
        
        is_valid = match_ratio >= 0.7 and len(missing) == 0
        needs_reparse = match_ratio < 0.5 or len(missing) > 1
        
        if is_valid:
            reason = f"Capper attribution matches expected: {len(matched)}/{len(expected_normalized)} matched"
        else:
            reason = f"Capper mismatch: expected {expected}, got {actual}. Missing: {missing}"
            if message_id:
                logging.warning(f"[MultiCapperVerifier] Message {message_id}: {reason}")
        
        return CapperVerificationResult(
            is_valid=is_valid,
            expected_cappers=expected,
            actual_cappers=actual,
            missing_cappers=missing,
            merged_cappers=[],
            confidence=match_ratio,
            needs_reparse=needs_reparse,
            reason=reason
        )
    
    @classmethod
    def _normalize_name(cls, name: str) -> str:
        """Normalize capper name for comparison."""
        # Remove @ symbol, lowercase, remove spaces/underscores
        normalized = name.lower()
        normalized = re.sub(r'^@', '', normalized)
        normalized = re.sub(r'[\s_\-]', '', normalized)
        return normalized
    
    @classmethod
    def _empty_result(cls) -> CapperVerificationResult:
        """Return empty result when no picks to verify."""
        return CapperVerificationResult(
            is_valid=True,
            expected_cappers=[],
            actual_cappers=[],
            missing_cappers=[],
            merged_cappers=[],
            confidence=0.5,
            needs_reparse=False,
            reason="No picks to verify"
        )
    
    @classmethod
    def generate_reparse_hint(
        cls,
        result: CapperVerificationResult,
        original_ocr: str = ""
    ) -> str:
        """Generate a hint for AI to reparse with correct capper attribution."""
        lines = [
            "### CAPPER ATTRIBUTION CORRECTION NEEDED",
            "",
            f"**Issue:** {result.reason}",
            ""
        ]
        
        if result.merged_cappers:
            lines.extend([
                "**MERGED NAMES DETECTED:**",
                "The following names appear to be multiple cappers merged together:",
            ])
            for merged in result.merged_cappers:
                lines.append(f"- '{merged}' should be SPLIT into separate cappers")
            lines.append("")
            lines.append("**INSTRUCTION:** Output SEPARATE pick objects for each capper!")
        
        if result.missing_cappers:
            lines.extend([
                "**MISSING CAPPERS:**",
                "These cappers were expected but not found in the output:",
            ])
            for missing in result.missing_cappers:
                lines.append(f"- {missing}")
            lines.append("")
            lines.append("**INSTRUCTION:** Look for picks belonging to these cappers in the OCR text!")
        
        if result.expected_cappers:
            lines.extend([
                "",
                "**EXPECTED CAPPER LIST:**",
                f"Based on the caption, these cappers should appear: {', '.join(result.expected_cappers)}",
                "",
                "**INSTRUCTION:** Each [OCR N] block corresponds to a different capper from this list.",
            ])
        
        return "\n".join(lines)


def verify_all_picks(
    messages: List[Dict[str, Any]],
    all_picks: List[Dict[str, Any]]
) -> Dict[int, CapperVerificationResult]:
    """
    Verify capper attribution for all messages.
    
    Returns dict of message_id -> CapperVerificationResult
    """
    from src.album_correlator import AlbumCorrelator
    
    # Group picks by message
    picks_by_message = {}
    for pick in all_picks:
        mid = pick.get('message_id', pick.get('id'))
        if mid not in picks_by_message:
            picks_by_message[mid] = []
        picks_by_message[mid].append(pick)
    
    results = {}
    
    for msg in messages:
        mid = msg.get('id')
        msg_picks = picks_by_message.get(mid, [])
        ocr_texts = msg.get('ocr_texts', [])
        image_paths = msg.get('images', [])
        caption = msg.get('text', '')
        
        # Get expected cappers from album correlation
        expected_cappers = []
        if len(image_paths) > 1:
            correlation = AlbumCorrelator.extract_and_correlate(
                caption, image_paths
            )
            expected_cappers = correlation.capper_names
        
        # Verify
        result = MultiCapperVerifier.verify_picks(
            picks=msg_picks,
            expected_cappers=expected_cappers,
            ocr_block_count=len(ocr_texts) if ocr_texts else len(image_paths),
            message_id=mid
        )
        
        results[mid] = result
    
    return results

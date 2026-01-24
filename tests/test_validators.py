"""
Test script for the new validation modules.
Run with: python test_validators.py
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_image_classifier():
    """Test the ImageClassifier module."""
    print("\n" + "="*60)
    print("TEST 1: ImageClassifier")
    print("="*60)
    
    from src.image_classifier import ImageClassifier, OCRStrategy
    
    # Test with a simple numpy array (simulated image)
    import numpy as np
    
    # Simulate a dark background image (should recommend Vision AI)
    dark_img = np.zeros((400, 600, 3), dtype=np.uint8)
    dark_img[:, :] = [30, 30, 30]  # Dark background
    
    analysis = ImageClassifier.classify_from_array(dark_img)
    print(f"Dark image analysis:")
    print(f"  Strategy: {analysis.strategy.value}")
    print(f"  Confidence: {analysis.confidence:.0%}")
    print(f"  Reasons: {analysis.reasons}")
    print(f"  Is dark background: {analysis.is_dark_background}")
    
    assert analysis.strategy == OCRStrategy.VISION_AI_REQUIRED, "Dark image should require Vision AI"
    print("  PASSED: Dark images route to Vision AI")
    
    # Simulate a bright document-style image (should recommend Tesseract)
    bright_img = np.ones((400, 600, 3), dtype=np.uint8) * 240  # Bright/white background
    
    analysis = ImageClassifier.classify_from_array(bright_img)
    print(f"\nBright image analysis:")
    print(f"  Strategy: {analysis.strategy.value}")
    print(f"  Confidence: {analysis.confidence:.0%}")
    print(f"  Reasons: {analysis.reasons}")
    
    assert analysis.strategy == OCRStrategy.TESSERACT_LIKELY, "Bright clean image should use Tesseract"
    print("  PASSED: Clean images route to Tesseract")
    
    return True


def test_album_correlator():
    """Test the AlbumCorrelator module."""
    print("\n" + "="*60)
    print("TEST 2: AlbumCorrelator")
    print("="*60)
    
    from src.album_correlator import AlbumCorrelator, generate_album_context
    
    # Test @mention extraction
    caption = "Picks from @Capper1, @Capper2, @Capper3 @cappersfree"
    image_paths = ["/img1.jpg", "/img2.jpg", "/img3.jpg"]
    
    result = AlbumCorrelator.extract_and_correlate(caption, image_paths)
    print(f"@mention extraction:")
    print(f"  Caption: {caption}")
    print(f"  Extracted cappers: {result.capper_names}")
    print(f"  Mappings: {result.mappings}")
    print(f"  Confidence: {result.confidence:.0%}")
    
    # Should extract 3 cappers (excluding 'cappersfree' watermark)
    assert len(result.capper_names) == 3, f"Should extract 3 cappers, got {len(result.capper_names)}"
    assert "cappersfree" not in [c.lower() for c in result.capper_names], "Should filter out watermarks"
    print("  PASSED: @mentions extracted and watermarks filtered")
    
    # Test numbered list
    caption2 = """
    1. KingCapper
    2. BetMaster
    3. PropKing
    """
    image_paths2 = ["/a.jpg", "/b.jpg", "/c.jpg"]
    
    result2 = AlbumCorrelator.extract_and_correlate(caption2, image_paths2)
    print(f"\nNumbered list extraction:")
    print(f"  Extracted cappers: {result2.capper_names}")
    
    assert len(result2.capper_names) >= 2, "Should extract cappers from numbered list"
    print("  PASSED: Numbered lists extracted")
    
    # Test context generation
    ocr_texts = ["Lakers -5 -110", "Chiefs ML +150", "Celtics Over 220"]
    context = generate_album_context(caption, ocr_texts, image_paths)
    print(f"\nGenerated album context (preview):")
    print(f"  {context[:200]}...")
    
    assert "IMAGE TO CAPPER MAPPING" in context, "Context should contain mapping section"
    print("  PASSED: Album context generated correctly")
    
    return True


def test_multi_pick_validator():
    """Test the MultiPickValidator module."""
    print("\n" + "="*60)
    print("TEST 3: MultiPickValidator")
    print("="*60)
    
    from src.multi_pick_validator import MultiPickValidator
    
    # Test pick count estimation from OCR text with multiple odds
    ocr_text = """
    Lakers -5 -110
    Chiefs ML +150
    Patriots -7.5 -105
    Celtics Over 220 -110
    """
    
    estimate = MultiPickValidator.estimate_pick_count(ocr_text)
    print(f"Pick count estimation:")
    print(f"  OCR text has 4 picks")
    print(f"  Estimated: {estimate.estimated_count}")
    print(f"  Confidence: {estimate.confidence:.0%}")
    print(f"  Signals: {estimate.signals}")
    
    assert estimate.estimated_count >= 3, f"Should estimate at least 3 picks, got {estimate.estimated_count}"
    print("  PASSED: Pick count estimated from odds patterns")
    
    # Test validation when extraction is incomplete
    parsed_picks = [
        {"message_id": 1, "pick": "Lakers -5", "capper_name": "Test"}
    ]  # Only 1 pick extracted
    
    result = MultiPickValidator.validate_extraction(
        ocr_text=ocr_text,
        parsed_picks=parsed_picks,
        message_id=1
    )
    print(f"\nValidation result (incomplete extraction):")
    print(f"  Expected: {result.expected_count}, Actual: {result.actual_count}")
    print(f"  Missing: {result.missing_count}")
    print(f"  Needs reparse: {result.needs_reparse}")
    print(f"  Reason: {result.reason}")
    
    assert result.needs_reparse, "Should flag for reparse when picks are missing"
    print("  PASSED: Incomplete extraction flagged for reparse")
    
    return True


def test_multi_capper_verifier():
    """Test the MultiCapperVerifier module."""
    print("\n" + "="*60)
    print("TEST 4: MultiCapperVerifier")
    print("="*60)
    
    from src.multi_capper_verifier import MultiCapperVerifier
    
    # Test merged name detection
    picks_with_merged = [
        {"message_id": 1, "capper_name": "KingCap, BetMaster", "pick": "Lakers -5"},
        {"message_id": 1, "capper_name": "PropKing", "pick": "Chiefs ML"}
    ]
    
    result = MultiCapperVerifier.verify_picks(picks_with_merged)
    print(f"Merged name detection:")
    print(f"  Picks have capper: 'KingCap, BetMaster' (merged)")
    print(f"  Is valid: {result.is_valid}")
    print(f"  Merged cappers detected: {result.merged_cappers}")
    print(f"  Needs reparse: {result.needs_reparse}")
    
    assert not result.is_valid, "Should detect merged names as invalid"
    assert len(result.merged_cappers) > 0, "Should identify merged capper names"
    print("  PASSED: Merged capper names detected")
    
    # Test with expected cappers from album
    picks_valid = [
        {"message_id": 1, "capper_name": "KingCap", "pick": "Lakers -5"},
        {"message_id": 1, "capper_name": "BetMaster", "pick": "Chiefs ML"}
    ]
    
    result2 = MultiCapperVerifier.verify_picks(
        picks=picks_valid,
        expected_cappers=["KingCap", "BetMaster"],
        ocr_block_count=2
    )
    print(f"\nExpected capper verification:")
    print(f"  Expected: ['KingCap', 'BetMaster']")
    print(f"  Actual: {result2.actual_cappers}")
    print(f"  Is valid: {result2.is_valid}")
    print(f"  Confidence: {result2.confidence:.0%}")
    
    assert result2.is_valid, "Should validate when cappers match expected"
    print("  PASSED: Capper attribution validated correctly")
    
    return True


def test_decoder_type_inference():
    """Test the decoder type inference and correction logic."""
    print("\n" + "="*60)
    print("TEST 5: Decoder Type Inference")
    print("="*60)
    
    from src.prompts.decoder import (
        infer_type_from_pick,
        normalize_pick_format,
        validate_and_correct_pick,
    )
    
    # Test cases for type inference
    test_cases = [
        # (pick_string, current_type, expected_type)
        ("New Hampshire -9", "Moneyline", "Spread"),  # Critical bug fix
        ("St Thomas -7", "Moneyline", "Spread"),  # Critical bug fix
        ("Chiefs -7.5", "Unknown", "Spread"),
        ("Lakers ML", "Unknown", "Moneyline"),
        ("Lakers ML", "Spread", "Moneyline"),  # ML explicit should win
        ("Lakers vs Celtics Over 220.5", "Spread", "Total"),
        ("De Minaur/Warriors MLP", "Moneyline", "Parlay"),  # MLP detection
        ("Youngstown St. / St. Thomas", "Moneyline", "Parlay"),  # Multi-team detection with /
        ("Chiefs & Bills", "Moneyline", "Parlay"),  # Multi-team detection with &
        ("1H Chiefs -3.5", "Spread", "Period"),
        ("Rams Super Bowl +225", "Moneyline", "Future"),  # Future detection
        ("LeBron: Pts Over 25.5", "Unknown", "Player Prop"),
        ("Luka Doncic 23+ PTS", "Unknown", "Player Prop"),  # Player prop with + format
    ]
    
    print("Type inference tests:")
    all_passed = True
    for pick_str, current_type, expected_type in test_cases:
        result = infer_type_from_pick(pick_str, current_type)
        passed = result == expected_type
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] '{pick_str}' ({current_type}) -> {result} (expected: {expected_type})")
        if not passed:
            all_passed = False
    
    assert all_passed, "Some type inference tests failed"
    print("  PASSED: All type inference tests passed")
    
    return True


def test_decoder_format_normalization():
    """Test the decoder format normalization logic."""
    print("\n" + "="*60)
    print("TEST 6: Decoder Format Normalization")
    print("="*60)
    
    from src.prompts.decoder import normalize_pick_format
    
    # Test cases for format normalization
    test_cases = [
        # (pick_string, bet_type, expected_output)
        ("U 221.5", "Total", "Under 221.5"),
        ("O 220", "Total", "Over 220"),
        ("LAKERS/CLIPPERS", "Total", "Lakers vs Clippers"),
        ("LAKERS&CELTICS", "Total", "Lakers vs Celtics"),
        ("Luka Doncic 23+ PTS", "Player Prop", "Luka Doncic: Pts Over 22.5"),
        # MLP parlays now get league prefixes (fix for grading errors)
        ("De Minaur/Warriors MLP", "Parlay", "(TENNIS) De Minaur ML / (NBA) Warriors ML"),
        ("CHIEFS", "Moneyline", "Chiefs"),  # Title case
    ]
    
    print("Format normalization tests:")
    all_passed = True
    for pick_str, bet_type, expected in test_cases:
        result = normalize_pick_format(pick_str, bet_type)
        passed = result == expected
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] '{pick_str}' ({bet_type}) -> '{result}' (expected: '{expected}')")
        if not passed:
            all_passed = False
    
    assert all_passed, "Some format normalization tests failed"
    print("  PASSED: All format normalization tests passed")
    
    return True


def test_decoder_full_pipeline():
    """Test the full decoder pipeline with validate_and_correct_pick."""
    print("\n" + "="*60)
    print("TEST 7: Decoder Full Pipeline")
    print("="*60)
    
    from src.prompts.decoder import validate_and_correct_pick
    
    # Test: Spread misclassified as ML (critical bug)
    pick = {
        "message_id": 31551,
        "capper_name": "TestCapper",
        "league": "NCAAB",
        "type": "Moneyline",  # WRONG - should be Spread
        "pick": "New Hampshire -9",
        "odds": -110,
        "units": 1.0,
    }
    
    result = validate_and_correct_pick(pick)
    print(f"Spread misclassification fix:")
    print(f"  Input type: {pick['type']}")
    print(f"  Output type: {result['type']}")
    print(f"  Output line: {result.get('line')}")
    
    assert result["type"] == "Spread", f"Should correct to Spread, got {result['type']}"
    assert result.get("line") == -9.0, f"Should extract line=-9.0, got {result.get('line')}"
    print("  PASSED: Spread misclassification corrected with line extracted")
    
    # Test: Player prop format normalization
    pick2 = {
        "message_id": 31540,
        "capper_name": "TestCapper",
        "league": "NBA",
        "type": "Player Prop",
        "pick": "Luka Doncic 23+ PTS",
        "odds": -110,
        "units": 1.0,
    }
    
    result2 = validate_and_correct_pick(pick2)
    print(f"\nPlayer prop format normalization:")
    print(f"  Input pick: {pick2['pick']}")
    print(f"  Output pick: {result2['pick']}")
    
    assert ":" in result2["pick"], "Should add colon format"
    assert "Over 22.5" in result2["pick"], f"Should convert 23+ to Over 22.5, got {result2['pick']}"
    print("  PASSED: Player prop formatted correctly")
    
    return True


def run_all_tests():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# RUNNING VALIDATOR MODULE TESTS")
    print("#"*60)
    
    results = {
        "ImageClassifier": test_image_classifier(),
        "AlbumCorrelator": test_album_correlator(),
        "MultiPickValidator": test_multi_pick_validator(),
        "MultiCapperVerifier": test_multi_capper_verifier(),
        "DecoderTypeInference": test_decoder_type_inference(),
        "DecoderFormatNormalization": test_decoder_format_normalization(),
        "DecoderFullPipeline": test_decoder_full_pipeline(),
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    all_passed = True
    for module, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {module}: {status}")
        if not passed:
            all_passed = False
    
    print("="*60)
    if all_passed:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

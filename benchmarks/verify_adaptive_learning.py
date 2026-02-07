import time
import os
import sys

# Ensure path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

from src.grading.parser import PickParser
from src.parsing.registry import TemplateRegistry

def test_adaptive_flow():
    print("--- Verifying Adaptive Learning Flow ---")
    
    # Reset Registry
    registry = TemplateRegistry()
    registry.templates = {}
    registry.save()
    registry._compiled_cache = {}
    
    # Test Cases: Distinct formats that Legacy might struggle with or just good candidates
    test_cases = [
        "🔥 Lakers -5.5 @ -110 (Max Bet) 🔥",
        "PADDY'S LOCK: Eagles -3 (-115) 5U",
        "WHALE PLAY: Chiefs -2.5 (10*)",
    ]
    
    for i, text in enumerate(test_cases):
        print(f"\n--- Case {i+1}: '{text}' ---")
        
        # Run 1: Cold Start
        print("Run 1 (Cold Start)...")
        t0 = time.time()
        pick_cold = PickParser.parse(text, league="NBA")
        dt_cold = time.time() - t0
        print(f"Cold Time: {dt_cold*1000:.2f}ms")
        if pick_cold:
            print(f"Result: {pick_cold.selection} {pick_cold.line} ({pick_cold.units}u)")
        else:
            print("Result: None (Failed)")
            
        # Run 2: Warm Start
        print("Run 2 (Warm Start)...")
        t0 = time.time()
        pick_warm = PickParser.parse(text, league="NBA")
        dt_warm = time.time() - t0
        print(f"Warm Time: {dt_warm*1000:.2f}ms")
        
        if pick_warm:
             print(f"Result: {pick_warm.selection} {pick_warm.line}")
        
        # Verify Speedup
        if dt_cold > 0 and dt_warm < dt_cold:
            speedup = dt_cold / dt_warm
            print(f"Speedup: {speedup:.1f}x")
        else:
            print("Speedup: None (Did it learn?)")
            
        # Check Registry to confirm it saved
        from src.parsing.fingerprinter import Fingerprinter
        fp = Fingerprinter.fingerprint(text)
        if registry.get_template(fp):
            print("Status: TEMPLATE SAVED ✅")
        else:
            print("Status: NO TEMPLATE ❌")

if __name__ == "__main__":
    test_adaptive_flow()

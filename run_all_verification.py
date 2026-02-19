import subprocess
import sys
import os
import time

def run_script(script_name: str):
    print(f"\n{'='*60}")
    print(f"RUNNING: {script_name}")
    print(f"{'='*60}")
    start_time = time.time()
    
    # Check if file exists
    if not os.path.exists(script_name):
        print(f"ERROR: Script {script_name} not found!")
        return False

    try:
        # Run the script and capture output
        # We allow stdout to flow through to see progress
        # But we check return code
        result = subprocess.run([sys.executable, script_name], check=False)
        
        duration = time.time() - start_time
        print(f"\nFinished {script_name} in {duration:.2f}s")
        
        if result.returncode == 0:
            print("STATUS: PASS")
            return True
        else:
            print(f"STATUS: FAIL (Return Code {result.returncode})")
            return False
            
    except Exception as e:
        print(f"CRITICAL ERROR executing {script_name}: {e}")
        return False

def main():
    print("STARTING COMPREHENSIVE VERIFICATION")
    print("Goal: 100% Confidence in Scraper Accuracy")
    print("-" * 60)
    
    params = {
        "validity": "test_validity.py",
        "golden_set": "verify_golden_set.py",
        "recall": "verify_picks.py"
    }
    
    results = {}
    
    # 1. Validity Filter Unit Tests
    # This checks if we are correctly identifying what IS and IS NOT a pick
    results["validity"] = run_script(params["validity"])
    
    # 2. Golden Set Verification
    # This checks end-to-end extraction on known labeled data
    results["golden_set"] = run_script(params["golden_set"])
    
    # 3. Recall Analysis (Missed Picks)
    # This checks recent raw logs for things we missed
    results["recall"] = run_script(params["recall"])
    
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"{name.upper():<15}: {status}")
        if not passed:
            all_passed = False
            
    if all_passed:
        print("\nOVERALL STATUS: GREEN (All Scripts Ran Successfully)")
        print("NOTE: Please inspect `verify_golden_set.py` output manually for accuracy %.")
    else:
        print("\nOVERALL STATUS: RED (Some Scripts Failed)")
        sys.exit(1)

if __name__ == "__main__":
    main()

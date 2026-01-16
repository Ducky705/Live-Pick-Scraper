
import sys
import os

# Add src folder to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from openrouter_client import DEFAULT_MODELS, VISION_MODELS

# VERIFIED WORKING FREE MODELS - Updated Jan 2026
EXPECTED_DEFAULT = [
    'google/gemini-2.0-flash-exp:free',      # Primary - confirmed working
    'mistralai/mistral-7b-instruct:free',    # Confirmed working for text
    'deepseek/deepseek-r1-0528:free',        # Large context, text-only
    'qwen/qwen3-coder:free',                 # Large context, text-only
]

EXPECTED_VISION = [
    'google/gemini-2.0-flash-exp:free',      # Primary - 1M context, confirmed vision
    'qwen/qwen-2.5-vl-7b-instruct:free',     # Backup vision (Qwen VL)
    'nvidia/nemotron-nano-12b-v2-vl:free',   # Backup vision (Nvidia)
    'allenai/molmo-2-8b:free',               # Backup vision (AllenAI)
]

def verify():
    print("Verifying Model Lists...")
    
    success = True
    
    # Check DEFAULT_MODELS
    if DEFAULT_MODELS != EXPECTED_DEFAULT:
        print(f"DEFAULT_MODELS mismatch:")
        print(f"  Expected: {EXPECTED_DEFAULT}")
        print(f"  Actual:   {DEFAULT_MODELS}")
        success = False
    else:
        print("DEFAULT_MODELS: OK")
        
    # Check VISION_MODELS
    if VISION_MODELS != EXPECTED_VISION:
        print(f"VISION_MODELS mismatch:")
        print(f"  Expected: {EXPECTED_VISION}")
        print(f"  Actual:   {VISION_MODELS}")
        success = False
    else:
        print("VISION_MODELS: OK")
    
    if success:
        print("\nSUCCESS: All model lists match verified working free models.")
    else:
        print("\nFAILED: Model lists need updating.")
        
    return success

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)

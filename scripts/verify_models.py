
import sys
import os

# Add src folder to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from openrouter_client import DEFAULT_MODELS

EXPECTED_ORDER = [
    'tngtech/deepseek-r1t2-chimera:free',    
    'google/gemini-2.0-flash-exp:free',      
    'mistralai/devstral-2512:free',          
    'z-ai/glm-4.5-air:free',                 
    'google/gemma-3-27b-it:free',            
    'meta-llama/llama-3.3-70b-instruct:free', 
    'nousresearch/hermes-3-llama-3.1-405b:free' 
]

def verify():
    print("Verifying Model Order...")
    
    if len(DEFAULT_MODELS) != len(EXPECTED_ORDER):
        print(f"FAILED: Length mismatch. Expected {len(EXPECTED_ORDER)}, got {len(DEFAULT_MODELS)}")
        return False
        
    for i, (actual, expected) in enumerate(zip(DEFAULT_MODELS, EXPECTED_ORDER)):
        if actual != expected:
            print(f"FAILED at index {i}:")
            print(f"  Expected: {expected}")
            print(f"  Actual:   {actual}")
            return False
            
    print("SUCCESS: Model order matches requirements.")
    return True

if __name__ == "__main__":
    if verify():
        sys.exit(0)
    else:
        sys.exit(1)

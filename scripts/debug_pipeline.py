#!/usr/bin/env python3
"""
Debug Script for CapperSuite
Run from terminal: python scripts/debug_pipeline.py

Tests:
1. Environment setup (API keys)
2. OCR quality on sample images
3. AI prompt generation and parsing
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment
from dotenv import load_dotenv
load_dotenv()

import json
import glob
from datetime import datetime

# Project imports
from src.ocr_handler import extract_text
from src.prompt_builder import generate_ai_prompt
from src.openrouter_client import openrouter_completion
from src.utils import clean_text_for_ai
from config import TEMP_IMG_DIR

def print_header(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def print_result(label, value, indent=0):
    prefix = "  " * indent
    if isinstance(value, str) and len(value) > 100:
        print(f"{prefix}📋 {label}:")
        for line in value[:500].split('\n'):
            print(f"{prefix}   {line}")
        if len(value) > 500:
            print(f"{prefix}   ... ({len(value) - 500} more chars)")
    else:
        print(f"{prefix}✅ {label}: {value}")

def test_env():
    """Test environment variables"""
    print_header("1. ENVIRONMENT CHECK")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:]
        print_result("OPENROUTER_API_KEY", masked)
    else:
        print("❌ OPENROUTER_API_KEY: NOT FOUND")
        print("   → Make sure your .env file exists and contains OPENROUTER_API_KEY=sk-...")
        return False
    
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    print_result("SUPABASE_URL", supabase_url[:30] + "..." if supabase_url else "NOT SET")
    print_result("SUPABASE_KEY", supabase_key[:8] + "..." if supabase_key else "NOT SET")
    
    return True

def test_ocr():
    """Test OCR on available images"""
    print_header("2. OCR QUALITY TEST")
    
    # Find sample images
    patterns = [
        os.path.join(TEMP_IMG_DIR, "*.jpg"),
        os.path.join(TEMP_IMG_DIR, "*.png"),
        "static/temp_images/*.jpg",
        "static/temp_images/*.png"
    ]
    
    images = []
    for pattern in patterns:
        images.extend(glob.glob(pattern))
    
    if not images:
        print("⚠️  No images found in temp directories")
        print(f"   Checked: {TEMP_IMG_DIR}")
        print("   → Run the app and fetch some messages first")
        return
    
    print(f"📷 Found {len(images)} images")
    
    # Test first 3 images
    for i, img_path in enumerate(images[:3]):
        print(f"\n--- Image {i+1}: {os.path.basename(img_path)} ---")
        
        # Make path relative for OCR handler
        rel_path = "/" + img_path.replace(os.getcwd() + "/", "")
        
        try:
            raw_ocr = extract_text(rel_path)
            print_result("Raw OCR Length", f"{len(raw_ocr)} chars")
            
            cleaned = clean_text_for_ai(raw_ocr)
            print_result("Cleaned Length", f"{len(cleaned)} chars (saved {len(raw_ocr) - len(cleaned)})")
            
            print_result("Sample Text", cleaned[:300] if cleaned else "[EMPTY]")
            
        except Exception as e:
            print(f"❌ OCR Error: {e}")

def test_prompt_generation():
    """Test AI prompt generation"""
    print_header("3. PROMPT GENERATION TEST")
    
    # Create mock messages
    mock_messages = [
        {
            "id": 12345,
            "text": "🔥 NBA POTD 🔥\nLakers -5.5 (-110)\n3 Units\n\nLet's ride! 🎯",
            "ocr_texts": ["KINGCAPPER VIP\nNBA Pick\nLos Angeles Lakers -5.5\nOdds: -110"],
            "channel_name": "TestChannel",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M ET")
        },
        {
            "id": 67890,
            "text": "NFL Sunday Lock\nChiefs ML",
            "ocr_texts": [],
            "channel_name": "ProPicks",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M ET")
        }
    ]
    
    print(f"📝 Generating prompt for {len(mock_messages)} mock messages...")
    
    try:
        prompt = generate_ai_prompt(mock_messages)
        print_result("Prompt Length", f"{len(prompt)} chars")
        print_result("Token Estimate", f"~{len(prompt) // 4} tokens")
        
        # Show key sections
        print("\n📄 PROMPT PREVIEW:")
        lines = prompt.split('\n')
        for line in lines[:20]:
            print(f"   {line[:80]}")
        print("   ...")
        
        return prompt
        
    except Exception as e:
        print(f"❌ Prompt Generation Error: {e}")
        return None

def test_ai_call(prompt):
    """Test actual AI call"""
    print_header("4. AI CALL TEST")
    
    if not prompt:
        print("⚠️  No prompt available, skipping AI test")
        return
    
    print("🤖 Calling OpenRouter API...")
    print("   Model: mistralai/devstral-2512:free")
    print("   (This may take 30-60 seconds)")
    
    try:
        import time
        start = time.time()
        
        result = openrouter_completion(prompt, "mistralai/devstral-2512:free", timeout=120)
        
        elapsed = time.time() - start
        print_result("Response Time", f"{elapsed:.1f} seconds")
        print_result("Response Length", f"{len(result)} chars")
        
        # Try to parse JSON
        try:
            parsed = json.loads(result)
            print_result("JSON Valid", "YES ✅")
            
            if isinstance(parsed, dict) and 'picks' in parsed:
                picks = parsed['picks']
                print_result("Picks Found", len(picks))
                
                for i, pick in enumerate(picks[:3]):
                    print(f"\n   Pick {i+1}:")
                    print(f"      ID: {pick.get('id')}")
                    print(f"      Capper: {pick.get('cn')}")
                    print(f"      League: {pick.get('lg')}")
                    print(f"      Pick: {pick.get('p')}")
                    print(f"      Odds: {pick.get('od')}")
            else:
                print_result("Response Structure", str(type(parsed)))
                print(f"   Keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'N/A'}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON Parse Error: {e}")
            print_result("Raw Response", result[:500])
            
    except Exception as e:
        print(f"❌ AI Call Error: {e}")

def main():
    print("\n" + "🔧 " * 20)
    print("       CAPPERSUITE DEBUG TOOLKIT")
    print("🔧 " * 20)
    
    # Run tests
    env_ok = test_env()
    
    if not env_ok:
        print("\n❌ Environment check failed. Fix issues above and retry.")
        return
    
    test_ocr()
    
    prompt = test_prompt_generation()
    
    # Ask before AI call (costs money/time)
    print("\n" + "-"*60)
    response = input("🤖 Run live AI test? (y/n): ").strip().lower()
    if response == 'y':
        test_ai_call(prompt)
    else:
        print("   Skipped AI test.")
    
    print_header("DEBUG COMPLETE")
    print("✅ All tests finished. Check results above for issues.")

if __name__ == "__main__":
    main()

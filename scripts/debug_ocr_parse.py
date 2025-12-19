#!/usr/bin/env python3
"""
OCR to AI Parse Debug Tool
Run: python scripts/debug_ocr_parse.py

Shows raw OCR vs AI parsing for real images from cappersfree channel
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import json
import glob
from datetime import datetime

from src.ocr_handler import extract_text
from src.prompt_builder import generate_ai_prompt
from src.openrouter_client import openrouter_completion
from src.utils import clean_text_for_ai

def find_channel_images(channel_pattern="cappersfree"):
    """Find images from a specific channel"""
    search_dirs = [
        "static/temp_images",
        "/Users/diegosargent/Documents/Programs/Telegram Scraper 2.0/static/temp_images"
    ]
    
    all_images = []
    for search_dir in search_dirs:
        if os.path.exists(search_dir):
            for ext in ['*.jpg', '*.png']:
                all_images.extend(glob.glob(os.path.join(search_dir, ext)))
    
    # Filter by channel pattern in filename
    filtered = [img for img in all_images if channel_pattern.lower() in img.lower()]
    
    # If no specific channel match, get any with good OCR content
    if not filtered:
        print(f"⚠️  No images matching '{channel_pattern}', using all images...")
        filtered = all_images
    
    return filtered[:5]  # Max 5 for testing

def process_image(img_path):
    """Process single image and show OCR"""
    rel_path = "/" + img_path.replace(os.getcwd() + "/", "")
    
    print(f"\n{'='*70}")
    print(f"📷 IMAGE: {os.path.basename(img_path)}")
    print(f"{'='*70}")
    
    # Raw OCR
    raw_ocr = extract_text(rel_path)
    print(f"\n🔤 RAW OCR ({len(raw_ocr)} chars):")
    print("-" * 50)
    if raw_ocr.strip():
        for line in raw_ocr.split('\n'):
            print(f"   {line}")
    else:
        print("   [EMPTY - No text detected]")
    
    # Cleaned OCR
    cleaned = clean_text_for_ai(raw_ocr)
    print(f"\n🧹 CLEANED OCR ({len(cleaned)} chars):")
    print("-" * 50)
    if cleaned.strip():
        print(f"   {cleaned}")
    else:
        print("   [EMPTY]")
    
    return raw_ocr, cleaned

def test_ai_parsing(messages):
    """Send messages to AI and show parsed result"""
    print(f"\n{'='*70}")
    print(f"🤖 AI PARSING TEST")
    print(f"{'='*70}")
    
    # Generate prompt
    prompt = generate_ai_prompt(messages)
    print(f"\n📝 Prompt size: {len(prompt)} chars (~{len(prompt)//4} tokens)")
    
    # Show the actual data section of the prompt
    print("\n📋 DATA SENT TO AI:")
    print("-" * 50)
    data_section = prompt.split("### **RAW DATA**")[-1] if "### **RAW DATA**" in prompt else prompt[-800:]
    for line in data_section.strip().split('\n')[:20]:
        print(f"   {line[:100]}")
    
    # Call AI
    print("\n⏳ Calling AI... (this may take 30-60s)")
    
    try:
        result = openrouter_completion(prompt, "mistralai/devstral-2512:free", timeout=120)
        
        print(f"\n✅ AI RESPONSE ({len(result)} chars):")
        print("-" * 50)
        
        # Parse JSON
        try:
            parsed = json.loads(result)
            
            if isinstance(parsed, dict) and 'picks' in parsed:
                picks = parsed['picks']
                print(f"\n🎯 EXTRACTED {len(picks)} PICKS:")
                print("-" * 50)
                
                for i, pick in enumerate(picks):
                    print(f"\n   Pick {i+1}:")
                    print(f"      Message ID:  {pick.get('id')}")
                    print(f"      Capper:      {pick.get('cn', 'Unknown')}")
                    print(f"      League:      {pick.get('lg', 'Unknown')}")
                    print(f"      Type:        {pick.get('ty', 'Unknown')}")
                    print(f"      Pick:        {pick.get('p', 'Unknown')}")
                    print(f"      Odds:        {pick.get('od', 'N/A')}")
                    print(f"      Units:       {pick.get('u', 1.0)}")
            else:
                print(f"   Response type: {type(parsed)}")
                print(f"   Raw: {json.dumps(parsed, indent=2)[:500]}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON Error: {e}")
            print(f"   Raw response: {result[:500]}")
            
    except Exception as e:
        print(f"❌ AI Error: {e}")

def main():
    print("\n" + "🔍 " * 20)
    print("     OCR → AI PARSE DEBUG TOOL")
    print("🔍 " * 20)
    
    # Find images
    channel = "cappersfree"
    print(f"\n🔎 Searching for images from '{channel}'...")
    
    images = find_channel_images(channel)
    
    if not images:
        print("❌ No images found. Run the main app and fetch messages first.")
        return
    
    print(f"✅ Found {len(images)} images to analyze")
    
    # Process each image
    messages = []
    for i, img_path in enumerate(images):
        raw_ocr, cleaned = process_image(img_path)
        
        # Build message for AI
        msg_id = hash(img_path) % 100000  # Fake ID based on path
        messages.append({
            "id": msg_id,
            "text": "",  # Caption would go here
            "ocr_texts": [cleaned] if cleaned else [],
            "channel_name": channel,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M ET")
        })
    
    # Now test AI parsing
    if messages:
        print("\n" + "-"*70)
        response = input("🤖 Run AI parsing on these images? (y/n): ").strip().lower()
        if response == 'y':
            test_ai_parsing(messages)
        else:
            print("   Skipped AI test.")
    
    print(f"\n{'='*70}")
    print("✅ DEBUG COMPLETE")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()

import asyncio
import os
import sys
import re
import csv
from datetime import datetime, timedelta

# Ensure we can import from local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db
from models import RawPick
from scrapers import TelegramScraper
import config

# Initialize Scraper to access its logic
scraper = TelegramScraper()

def analyze_extraction_logic(raw_text, channel_title, channel_id):
    """
    Simulates the _extract_capper_name method but returns a log of decisions.
    """
    logs = []
    
    # 1. Clean Lines
    full_text = raw_text.replace("[OCR RESULT (Combines 3 Passes)]:", "").strip()
    lines = [l.strip() for l in full_text.split('\n') if l.strip()]
    
    logs.append(f"   Input Lines ({len(lines)}):")
    for i, l in enumerate(lines[:3]):
        logs.append(f"     [{i}] '{l}'")

    is_aggregator = (channel_id in config.AGGREGATOR_CHANNEL_IDS) or ("CAPPERS" in channel_title.upper())
    logs.append(f"   Is Aggregator? {is_aggregator}")

    # Default Fallback
    fallback_name = scraper._clean_capper_name(channel_title)
    if "CAPPERS" in fallback_name.upper() or "FREE PICKS" in fallback_name.upper():
        fallback_name = "Unknown Capper"
        logs.append(f"   Fallback Name set to 'Unknown Capper' (Generic Channel detected)")
    else:
        fallback_name = re.sub(r'(free|capper|picks|locks|betting|official)', '', fallback_name, flags=re.I).strip()
        if len(fallback_name) < 3: 
            fallback_name = "Unknown Capper"
        logs.append(f"   Fallback Name calculated: '{fallback_name}'")

    if not lines:
        return fallback_name, logs

    if is_aggregator:
        # Check Line 0
        candidate = scraper._clean_capper_name(lines[0])
        logs.append(f"   Checking Line 0: '{candidate}'")
        
        if candidate.startswith("@"):
            return candidate.replace("@", "").strip(), logs
        
        if scraper._is_invalid_name(candidate):
            logs.append(f"     ❌ Invalid (Regex Match/Length)")
        elif candidate.lower() in config.BLACKLISTED_CAPPERS:
            logs.append(f"     ❌ Blacklisted")
        else:
            logs.append(f"     ✅ Valid Name Found!")
            return candidate, logs
        
        # Check Line 1
        if len(lines) > 1:
            candidate_2 = scraper._clean_capper_name(lines[1])
            logs.append(f"   Checking Line 1: '{candidate_2}'")
            if not scraper._is_invalid_name(candidate_2) and len(candidate_2) < 30:
                logs.append(f"     ✅ Valid Name Found!")
                return candidate_2, logs
            else:
                logs.append(f"     ❌ Invalid")

    logs.append(f"   ⚠️ No internal name found. Using Fallback.")
    return fallback_name, logs

async def main():
    print("="*60)
    print("🕵️ CAPPER NAME EXTRACTION DEBUGGER")
    print("="*60)

    if not db.client:
        print("❌ Error: Database client not initialized.")
        return

    # Fetch last 50 picks
    print("📥 Fetching recent picks...")
    res = db.client.table('live_raw_picks').select('*').order('created_at', desc=True).limit(50).execute()
    picks = [RawPick(**p) for p in res.data]

    export_data = []

    for i, pick in enumerate(picks):
        print(f"\nMessage #{i+1} (ID: {pick.id})")
        print("-" * 40)
        
        # We simulate the channel title because we don't have it in the DB per se, 
        # but usually the "capper_name" in DB *was* the channel title in the old code.
        # For this test, let's assume the channel was "CAPPERS FREE🚨" since that's what we saw in logs.
        simulated_channel_title = "CAPPERS FREE🚨"
        
        # RE-RUN LOGIC
        calculated_name, decision_log = analyze_extraction_logic(
            pick.raw_text, 
            simulated_channel_title, 
            999 # Fake ID to force aggregator logic
        )
        
        print("\n".join(decision_log))
        print(f"👉 FINAL DECISION: '{calculated_name}'")
        
        # Check if it matches what's in DB
        db_status = "✅ MATCH" if pick.capper_name == calculated_name else "❌ DIFF"
        print(f"   (DB has: '{pick.capper_name}') -> {db_status}")

        export_data.append({
            "id": pick.id,
            "calculated_name": calculated_name,
            "db_name": pick.capper_name,
            "raw_text_snippet": pick.raw_text[:100].replace("\n", " "),
            "decision_log": " | ".join(decision_log)
        })

    # Export
    filename = "capper_debug_report.csv"
    keys = export_data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        dict_writer = csv.DictWriter(f, keys)
        dict_writer.writeheader()
        dict_writer.writerows(export_data)

    print("\n" + "="*60)
    print(f"📄 EXPORT SAVED: {os.path.abspath(filename)}")
    print("Send this file to debugging if results are still wrong.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
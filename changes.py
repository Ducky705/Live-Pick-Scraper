import asyncio
import os
import logging
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load env vars
load_dotenv()

# Setup logging to show everything
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_and_debug():
    print("="*60)
    print("🔧 PROCESSOR DIAGNOSTIC TOOL")
    print("="*60)

    # 1. Check Credentials
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    ai_key = os.getenv('OPENROUTER_API_KEY')
    ai_model = os.getenv('AI_PARSER_MODEL')

    print(f"Checking Config:")
    print(f"  - Supabase URL:   {'✅ Found' if url else '❌ MISSING'}")
    print(f"  - Supabase Key:   {'✅ Found' if key else '❌ MISSING'}")
    print(f"  - AI API Key:     {'✅ Found' if ai_key else '❌ MISSING'}")
    print(f"  - AI Model:       {ai_model}")

    if not all([url, key, ai_key]):
        print("\n❌ STOPPING: Missing credentials in .env file.")
        return

    # 2. Reset Failed Attempts in DB
    print("\n1. Resetting 'process_attempts' for today's picks...")
    db = create_client(url, key)
    
    try:
        # Reset picks from the last 24 hours so we can retry them
        res = db.table('live_raw_picks') \
            .update({'process_attempts': 0, 'status': 'pending'}) \
            .gt('id', 0) \
            .execute()
        print(f"   ✅ Reset complete. Ready to re-process.")
    except Exception as e:
        print(f"   ❌ DB Connection Failed: {e}")
        return

    # 3. Import Processing Service (Dynamic Import to use local env)
    print("\n2. Starting Processor (Watch for RED errors below)...")
    print("-" * 60)
    
    try:
        from processing_service import process_picks
        process_picks()
    except Exception as e:
        print(f"\n❌ CRITICAL FAILURE: {e}")

    print("-" * 60)
    print("Diagnostic finished.")

if __name__ == "__main__":
    reset_and_debug()
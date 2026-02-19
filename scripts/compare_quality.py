import logging
import os
import sys
import json
import time

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv
load_dotenv()

from src.cerebras_client import cerebras_completion
from src.gemini_client import gemini_text_completion
from src.prompt_builder import generate_ai_prompt

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def compare_quality():
    logger.info("Running Head-to-Head: Cerebras vs Gemini 2.0 Flash")
    
    examples = [
        {
            "id": 101,
            "desc": "Complex Parlay",
            "text": """
            🔥 PARLAY ALERT 🔥
            (NBA) Lakers -5 
            (NCAAB) Duke ML
            (NHL) Bruins 60-Min Line
            Odds: +550
            Units: 2u
            Let's ride! 🚀
            """
        },
        {
            "id": 102,
            "desc": "Player Props (Messy)",
            "text": """
            LeBron James o25.5 pts
            AD u12.5 rebs
            Steph Curry over 4.5 3PM
            Thinking these hit easily.
            """
        },
        {
            "id": 103,
            "desc": "Marketing Noise (Should Extract Nothing)",
            "text": """
            WHALE PLAY COMING SOON 🐋
            JOIN THE VIP FOR 50% OFF
            GUARANTEED WINS
            DM ME FOR INFO
            NO FREE PLAYS HERE
            """
        }
    ]
    
    scores = {"cerebras": 0, "gemini": 0}
    
    # Focus on Gemini for this run (Cerebras already proven)
    target_ex = examples[1] # Player Props
    
    logger.info(f"\n{'='*60}")
    logger.info(f"TEST: {target_ex['desc']}")
    logger.info(f"{'='*60}")
    
    data_item = [{"id": target_ex['id'], "text": target_ex['text']}]
    prompt = generate_ai_prompt(data_item)
    
    logger.info("Waiting 5s for rate limits...")
    time.sleep(5)
    
    logger.info("\n--- Gemini (2.0 Flash) ---")
    start = time.time()
    try:
        g_res = gemini_text_completion(prompt, model="gemini-2.0-flash", timeout=20)
        g_time = time.time() - start
        logger.info(f"Time: {g_time:.2f}s")
        print(f"Output: {g_res}")
    except Exception as e:
        logger.error(f"Gemini Failed: {e}")
            
    logger.info("\nDone.")

if __name__ == "__main__":
    compare_quality()

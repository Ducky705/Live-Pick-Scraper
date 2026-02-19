import json
import os
import sys
import logging

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.extraction_pipeline import ExtractionPipeline
from src.rule_based_extractor import RuleBasedExtractor
from src.config import OUTPUT_DIR

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugFailures")

TARGET_IDS = ["11211", "2022538739126333839"]

def load_target_messages():
    source_file = os.path.join(OUTPUT_DIR, "debug_msgs.json")
    with open(source_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    targets = [m for m in data if str(m.get("id")) in TARGET_IDS]
    return targets

def debug_failures():
    messages = load_target_messages()
    logger.info(f"Loaded {len(messages)} target messages.")
    
    for msg in messages:
        mid = str(msg.get("id"))
        logger.info(f"--- Debugging Message {mid} ---")
        
        # 1. Test Rule-Based Extraction
        logger.info("Running RuleBasedExtractor...")
        rule_picks, _ = RuleBasedExtractor.extract([msg])
        logger.info(f"Rule-Based Picks: {len(rule_picks)}")
        for p in rule_picks:
            logger.info(f"  - {p}")

        # 2. Test Full Pipeline (AI)
        logger.info("Running Full Pipeline...")
        all_picks = ExtractionPipeline.run([msg], target_date="2026-02-14", strategy="groq")
        logger.info(f"Pipeline Picks: {len(all_picks)}")
        for p in all_picks:
            logger.info(f"  - {p}")
            
if __name__ == "__main__":
    debug_failures()

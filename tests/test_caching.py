import time
import sys
import os
import logging

sys.path.insert(0, os.path.abspath("."))
from src.extraction_pipeline import ExtractionPipeline
from src.rule_based_extractor import RuleBasedExtractor

# Setup logging to see cache hits
logging.basicConfig(level=logging.INFO)

def test_caching():
    print("Testing ExtractionPipeline Caching...")
    
    # Create duplicate messages
    messages = [
        {"id": "1", "text": "Lakers -5 2U", "source": "telegram"},
        {"id": "2", "text": "Celtics ML 5U", "source": "telegram"},
        {"id": "3", "text": "Lakers -5 2U", "source": "discord"}, # Duplicate content, diff ID
        {"id": "4", "text": "Unique Message", "source": "twitter"}
    ]
    
    # First Run
    start = time.time()
    results1 = ExtractionPipeline.run(messages, "2026-02-05", strategy="round_robin")
    end = time.time()
    t1 = end - start
    print(f"Run 1 Time: {t1:.4f}s. Picks: {len(results1)}")
    
    # Second Run (Same messages, different IDs to Simulate flow)
    messages_new = [
        {"id": "5", "text": "Lakers -5 2U", "source": "telegram"},
        {"id": "6", "text": "Celtics ML 5U", "source": "telegram"},
    ]
    
    start = time.time()
    results2 = ExtractionPipeline.run(messages_new, "2026-02-05", strategy="round_robin")
    end = time.time()
    t2 = end - start
    print(f"Run 2 Time: {t2:.4f}s. Picks: {len(results2)}")
    
    if t2 < t1 * 0.5:
        print("SUCCESS: Run 2 was significantly faster (Cache Hit).")
    else:
        print("WARNING: Run 2 was not significantly faster (Cache Miss?).")

if __name__ == "__main__":
    test_caching()

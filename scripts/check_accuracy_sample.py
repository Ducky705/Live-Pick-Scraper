import logging
import os
import sys
import json

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.parallel_batch_processor import parallel_processor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

def test_accuracy():
    logger.info("Testing Provider Accuracy with Real Pick Data...")
    
    # Real sample message
    sample_text = """
    NBA
    Lakers -5
    Celtics vs Lakers Over 220.5
    LeBron James Over 25.5 Pts
    Thinking Lakers cover easily here.
    """
    
    providers = ["cerebras", "mistral", "gemini"]
    
    # Send enough batches to cycle through all providers (Groq[fail], Cerebras, Mistral, Gemini)
    # The striper stripes across available workers. 
    # Workers: Groq(1), Cerebras(5), Mistral(8), Gemini(3) = 17 total.
    # To hit Gemini, we might need a few.
    # Let's send 10 batches.
    batches = []
    for i in range(10): 
        batch = [{
            "id": 5000 + i, 
            "text": sample_text,
        }]
        batches.append(batch)
    
    logger.info(f"Sending {len(batches)} batches...")
    results = parallel_processor.process_batches(batches)
    
    logger.info("\n=== RESULTS ===")
    for i, res in enumerate(results):
        if res:
            logger.info(f"\nBatch {i} Result:")
            try:
                # Result is the JSON string itself (data)
                if isinstance(res, str):
                   json_data = json.loads(res)
                   # Pretty print slightly compact
                   print(json.dumps(json_data))
                   picks = json_data.get("picks", [])
                   logger.info(f"Extracted {len(picks)} picks.")
                else:
                   logger.info(f"Unexpected type: {type(res)}")
            except Exception as e:
                logger.error(f"Invalid JSON or parse error: {e} | Data: {str(res)[:100]}")
        else:
             logger.error(f"Batch {i} failed (None)")

if __name__ == "__main__":
    test_accuracy()

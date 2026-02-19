import logging
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.parallel_batch_processor import parallel_processor

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def test_providers():
    logger.info("Testing all configured providers...")
    
    providers = ["groq", "cerebras", "mistral", "gemini"]
    
    # Create simple batches
    batches = []
    for i, p in enumerate(providers):
        # Data items must have 'id' and 'text' as expected by prompt_builder
        batch = [{"id": 1000 + i, "text": f"Hello {p}, identify yourself."}]
        batches.append(batch)
    
    # Process with parallel processor (force specific provider for each batch)
    # Since process_batches stripes, we can just pass the list and see who picks what up
    # But to be sure, we'll confirm the output.
    
    # Actually, parallel_processor.process_batches takes a list of batches.
    # We want to force each provider to be tested.
    # parallel_processor doesn't easily allow forcing a specific provider for a specific batch in the public API 
    # without mocking or internal manipulation, but we can try to run it and seeing if everyone contributes.
    
    # Better approach: check individual clients if possible, or use the processor's _execute_request if accessible, 
    # but that's protected.
    
    # Let's try sending 8 batches (enough to trigger all workers if they are free)
    # Replicate the provider-specific batches to ensure coverage
    test_batches = batches * 2
    
    results = parallel_processor.process_batches(test_batches)
    
    logger.info(f"Processed {len(results)} batches.")
    for res in results:
        if res:
            logger.info(f"Result: {res[:50]}...")
        else:
            logger.error("Got None result")
            
    # Check stats
    logger.info("Provider Stats:")
    for p in providers:
        stats = parallel_processor.stats.get(p, {})
        logger.info(f"{p}: {stats}")
        if stats.get("count", 0) == 0:
            logger.warning(f"Provider {p} was not used! (This might be due to striping logic or errors)")

if __name__ == "__main__":
    test_providers()

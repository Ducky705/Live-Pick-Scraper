import os
import sys

# Ensure path is loaded
sys.path.insert(0, r'd:\Programs\Sports Betting\TelegramScraper\v0.0.15')

# Patch PROVIDER_CONFIG before importing ParallelBatchProcessor
import src.parallel_batch_processor as parallel_module

# Override the configuration for OpenRouter to specifically target our model
parallel_module.PROVIDER_CONFIG["openrouter"]["model"] = "arcee-ai/trinity-large-preview:free"

# Also directly configure DEFAULT_MODELS in openrouter_client
import src.openrouter_client as openrouter_module
openrouter_module.DEFAULT_MODELS = ['arcee-ai/trinity-large-preview:free']

# Now run the benchmark
import benchmark_golden_set
benchmark_golden_set.run_benchmark()

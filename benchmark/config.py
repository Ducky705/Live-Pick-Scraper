# benchmark/config.py
"""
Benchmark Configuration - All models and settings.
"""

# Number of runs per model per test case (for variance measurement)
# Use --runs flag to increase for more accurate variance stats
DEFAULT_RUNS = 1

# Timeout per API request (seconds) - reduced for faster failure detection
REQUEST_TIMEOUT = 60

# Delay between API calls to avoid rate limiting (seconds)
RATE_LIMIT_DELAY = 0.3

# Maximum concurrent requests (set to 1 for sequential to avoid rate limits)
MAX_CONCURRENT = 1

# All OpenRouter models to benchmark
MODELS_TO_TEST = [
    # --- Vision-Capable Models (can process images directly) ---
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "qwen/qwen-2.5-vl-7b-instruct:free",
    
    # --- Text-Only Models (use OCR text) ---
    "xiaomi/mimo-v2-flash:free",
    "mistralai/devstral-2512:free",
    "kwaipilot/kat-coder-pro:free",
    "tngtech/deepseek-r1t2-chimera:free",
    "nex-agi/deepseek-v3.1-nex-n1:free",
    "tngtech/deepseek-r1t-chimera:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "z-ai/glm-4.5-air:free",
    "tngtech/tng-r1t-chimera:free",
    "qwen/qwen3-coder:free",
    "deepseek/deepseek-r1-0528:free",
    "google/gemma-3-27b-it:free",
    "allenai/olmo-3.1-32b-think:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "google/gemini-2.0-flash-exp:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "meta-llama/llama-3.1-405b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "arcee-ai/trinity-mini:free",
    "qwen/qwen3-4b:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "moonshotai/kimi-k2:free",
    "google/gemma-3-4b-it:free",
]

# Vision-capable models (will receive base64 images)
VISION_MODELS = {
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "qwen/qwen-2.5-vl-7b-instruct:free",
}

# Quick test models (for development/quick checks)
QUICK_TEST_MODELS = [
    "mistralai/devstral-2512:free",
    "google/gemma-3-4b-it:free",
]

def is_vision_model(model_name: str) -> bool:
    """Check if a model supports vision (image input)."""
    return model_name in VISION_MODELS or "vl" in model_name.lower() or "vision" in model_name.lower()

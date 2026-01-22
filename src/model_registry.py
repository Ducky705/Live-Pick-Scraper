"""
Model Registry
==============
Catalogs all available FREE models across providers for benchmarking and production use.

MAXIMUM SPEED Configuration - Updated January 22, 2026

Rate Limits Summary:
- Groq: 1000 RPM, 250-300K TPM (PRIMARY - 16 concurrent)
- Mistral: 60 RPM, 500K TPM (SECONDARY - 4 concurrent, batch 10)
- Gemini: 10-15 RPM, 250K TPM (TERTIARY - 3 concurrent)
- Cerebras: 30 RPM, 60K TPM (OVERFLOW - 2 concurrent)
- OpenRouter: FALLBACK ONLY (3-120s latency, not recommended)
"""

# =============================================================================
# GROQ MODELS (Direct API - groq_client.py) - PRIMARY PROVIDER
# 1000 RPM, 250-300K TPM, 16 concurrent workers
# =============================================================================
GROQ_MODELS = [
    "llama-3.3-70b-versatile",    # 280 t/s, best quality (DEFAULT)
    "llama-3.1-8b-instant",       # 560 t/s, fastest
    "openai/gpt-oss-120b",        # 500 t/s, GPT OSS 120B
    "openai/gpt-oss-20b",         # 1000 t/s, GPT OSS 20B (fastest new)
]

# =============================================================================
# MISTRAL MODELS (Direct API - mistral_client.py) - SECONDARY PROVIDER
# 60 RPM, 500K TPM (can batch 10 messages per call!)
# =============================================================================
MISTRAL_MODELS = [
    # Large models
    "mistral-large-latest",       # mistral-large-2512
    "mistral-large-2411",         # Older large
    
    # Small models  
    "mistral-small-latest",       # mistral-small-2506
    "mistral-small-2501",         # Older small
    "mistral-saba-2502",          # Saba variant
    
    # Code models
    "codestral-latest",           # codestral-2508 (DEFAULT for parsing)
    "codestral-2501",             # Older codestral
    
    # Mini models (fastest)
    "ministral-8b-latest",        # ministral-8b-2512
    "ministral-8b-2410",          # Older 8B
    "ministral-3b-2410",          # Tiny 3B
    
    # MoE models
    "open-mixtral-8x22b",         # Large MoE
    "open-mistral-nemo",          # Nemo 12B
    
    # Vision models (can do text too)
    "pixtral-large-latest",       # pixtral-large-2411
    "pixtral-12b-2409",           # Smaller pixtral
]

# =============================================================================
# GEMINI MODELS (Direct API - gemini_client.py) - TERTIARY PROVIDER
# 10-15 RPM, 250K TPM, 3 concurrent workers
# =============================================================================
GEMINI_MODELS = [
    "gemini-2.5-flash-lite",      # 15 RPM - highest (DEFAULT)
    "gemini-2.5-flash",           # 10 RPM
    "gemini-2.0-flash",           # 10 RPM
    "gemini-2.0-flash-lite",      # Gemini 2.0 Flash-Lite
]

# =============================================================================
# CEREBRAS MODELS (Direct API - cerebras_client.py) - OVERFLOW PROVIDER
# 30 RPM, 60K TPM, 2 concurrent workers
# =============================================================================
CEREBRAS_MODELS = [
    "llama-3.3-70b",              # Best quality (~2100 t/s)
    "llama3.1-8b",                # Fast (~2200 t/s)
    "qwen-3-32b",                 # Qwen 3 32B (~2600 t/s)
    "gpt-oss-120b",               # GPT OSS 120B (~3000 t/s)
]

# =============================================================================
# OPENROUTER MODELS (Free Tier) - FALLBACK ONLY (3-120s latency)
# NOT RECOMMENDED for speed-critical operations
# =============================================================================
OPENROUTER_MODELS = [
    # DeepSeek (reasoning model - slow but accurate)
    "deepseek/deepseek-r1-0528:free",
    
    # Meta Llama
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-405b-instruct:free",
    
    # Google Gemma/Gemini
    "google/gemini-2.0-flash-exp:free",
    "google/gemma-3-27b-it:free",
    "google/gemma-3-12b-it:free",
    
    # NVIDIA
    "nvidia/nemotron-3-nano-30b-a3b:free",
    
    # Arcee
    "arcee-ai/trinity-mini:free",
    
    # Mistral (via OpenRouter)
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "mistralai/devstral-2512:free",
    
    # Moonshot
    "moonshotai/kimi-k2:free",
]

# =============================================================================
# MASTER REGISTRY
# =============================================================================
MODEL_REGISTRY = {
    "gemini": GEMINI_MODELS,
    "mistral": MISTRAL_MODELS,
    "groq": GROQ_MODELS,
    "cerebras": CEREBRAS_MODELS,
    "openrouter": OPENROUTER_MODELS
}

def get_all_models():
    """Return a flat list of all (provider, model) tuples."""
    all_models = []
    for provider, models in MODEL_REGISTRY.items():
        for model in models:
            all_models.append((provider, model))
    return all_models

def get_models_for_provider(provider: str):
    """Return list of models for a specific provider."""
    return MODEL_REGISTRY.get(provider, [])

def count_models():
    """Return total count of registered models."""
    return sum(len(models) for models in MODEL_REGISTRY.values())

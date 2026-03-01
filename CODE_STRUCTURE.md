# CapperSuite Live - Code Structure

This document outlines the architecture and structure of the `CapperSuite Live` repository, optimized for 24/7 event-driven production usage.

## Directory Layout

```text
/
├── benchmark/              # "Golden Set" validation & performance measuring tools
├── data/                   # Runtime state (cache.db, logs, debug_, images) - .gitignored
├── deploy/                 # Dockerfile and start.sh for production hosting
├── src/                    # Core Application Domain
│   ├── config.py           # Centralized configuration and environment parser
│   ├── live_pipeline.py    # MAIN ORCHESTRATOR: Image Encoding -> AI Routing -> Fallbacks
│   ├── live_supabase.py    # Custom DB Client Wrapper for Live Pick ingestion
│   ├── live_extensions.py  # Discord & Twitter WS integration logic
│   ├── capper_matcher.py   # Fuzzy heuristic team/capper matching logic (SmartMatch)
│   ├── discord_client.py   # Standalone Discord bot logic
│   ├── twitter_client.py   # Standalone web-scraping logic for Twitter 
│   ├── supabase_client.py  # Low-level Supabase REST API constructor
│   ├── models.py           # Pydantic data models 
│   └── utils_urllib.py     # Custom lightweight HTTP module replacing `requests`
├── tests/                  # Pytest automated test suite
├── tools/                  # Script maintenance tools
├── live_runner.py          # 24/7 DAEMON / CLI Entry Point
├── pyproject.toml          # packaging config
└── requirements.txt        # Dependency manifest
```

## Data Flow: Live Ingestion Pipeline

The current system relies exclusively on event-listeners triggering the pipeline asynchronously.

1. **Ingestion (`live_runner.py & live_extensions.py`)**: Asynchronous continuous polling over Telegram, Twitter, and Discord.
2. **Deduplication**: Creates a composite ID from the target Platform + Account ID + Message ID. Attempts database Insert with `ignore_duplicates=True`. If collision occurs, process aborts immediately.
3. **Payload Preparation**: Downloads any attached image media directly into `/data/temp_images/`.
4. **AI Parsing Strategy (`src/live_pipeline.py`)**: 
   - **Text Only Events:** Try OpenRouter (Stepfun) -> fallback to Google Gemini -> fallback to Mistral.
   - **Vision (Image) Events:** Encode image to `base64`. Try Google Gemini -> fallback to Mistral -> fallback to OpenRouter.
5. **Resolution (`src/capper_matcher.py`)**: Attempts standardizing aliases utilizing the cached directory in Supabase.
6. **Delivery (`src/live_supabase.py`)**: Maps extracted values into a strict JSON architecture and pushes straight into the `live_structured_picks` analytical table using REST UPSERT logic.

## AI Design Methodology

This app is explicitly restricted from auto-crashing. Errors must be gracefully captured and recorded to the log state under the `[CHANNEL_NAME]` tag. Never write fatal system exceptions inside ingestion handlers.

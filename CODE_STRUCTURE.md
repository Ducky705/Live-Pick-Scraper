# CapperSuite CLI - Code Structure
This document outlines the architecture and structure of the CapperSuite CLI after its production-readiness refactor.

## Directory Layout

```text
/
├── benchmark/              # "Golden Set" validation & performance measuring tools
│   ├── dataset/            # JSON/Txt data containing golden set ground truths
│   ├── runners/            # Sub-scripts for running specific types of benchmarks
│   ├── reports/            # Output reports from benchmark runs
│   └── benchmark_golden_set.py
├── client/                 # Vite dashboard application (public assets, UI)
├── data/                   # Runtime state (cache.db, logs, debug_, images) - .gitignored
├── docs/                   # subsystem documentation (OCR.md, GRADING.md)
├── scripts/                # Operational tooling and specific scraping tasks
├── src/                    # Application Source Code
│   ├── config.py           # Centralized configuration and environment parser
│   ├── client/             # External API clients (discord, telegram, twitter)
│   ├── enrichment/         # Pick data enrichment (odds backfilling, game matching)
│   ├── grading/            # V3 Grading Engine (ESPN scraping, parsing, matching)
│   │   ├── engine.py       # Main grading logic & bet type handlers
│   │   ├── matcher.py      # Fuzzy team matching logic
│   │   ├── parser.py       # Syntax parsing for raw picks
│   │   └── constants.py    # League/Team/Stat mappings
│   ├── parsers/            # Raw text/HTML parsers
│   ├── parsing/            # AI Parsing logic & prompt schemas
│   ├── prompts/            # LLM Prompt templates (system prompts, few-shot examples)
│   ├── data/               # Persistent application data assets (if any)
│   ├── utils/              # Shared helpers (logging, string cleaning)
│   ├── extraction_pipeline.py  # MAIN ORCHESTRATOR: Scrape -> OCR -> AI -> Validate
│   ├── parallel_batch_processor.py # Manages multi-provider cascading AI requests
│   ├── consensus_engine.py     # "The Council" multi-model voting logic
│   ├── provider_pool.py        # AI Provider load balancing (Urllib/Groq focus)
│   ├── rule_based_extractor.py # Regex/Heuristic extraction (Pass 1)
│   └── models.py           # Pydantic data models (BetPick, TelegramMessage)
├── tests/                  # Pytest automated test suite
├── tools/                  # Script maintenance tools
├── cli_tool.py             # CLI Entry Point
├── pyproject.toml          # Linting, typing and packaging config
└── requirements.txt        # Dependency manifest
```

## Data Flow: Extraction Pipeline

The core functionality of CapperSuite is orchestrated by the `ExtractionPipeline`. Here is how a raw message becomes a graded pick:

1. **Ingestion (`cli_tool.py`)**: Fetches messages from Telegram, Twitter, and Discord.
2. **Deduplication (`deduplicator.py`)**: Merges identical messages to reduce duplicate work. 
3. **Auto-classification (`auto_processor.py`)**: Heuristically decides if a message contains a pick or should be discarded.
4. **OCR & Image Extractor (`ocr_cascade.py`)**: If the message contains images, attempts RapidOCR, and escalates to Vision models if needed.
5. **Rule-Based Extractor (`rule_based_extractor.py`)**: Fast first-pass extraction using regular expressions for standard formats.
6. **AI Parsing (`parallel_batch_processor.py`)**: Messages too complex for regex are handed to AI models (Groq/Gemini), batched together for high throughput.
7. **Normalizer & Validator (`pick_normalizer.py`, `semantic_validator.py`)**: Standardizes outputs, resolves conflicting teams, and catches hallucinated or malformed answers.
8. **Grading (`grading/engine.py`)**: Compares standardized picks to live/historical ESPN scores to determine Win/Loss/Push/Pending.

## Core Models (`models.py`)

- **`TelegramMessage`**: Represents raw ingested message structure.
- **`BetPick`**: The heavily-validated ultimate outcome object containing capper info, the pick string, standardized team names, odds, bet type, and the final grade.

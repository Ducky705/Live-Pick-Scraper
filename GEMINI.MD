# GEMINI.MD - Context Source of Truth

## Project Overview
**CapperSuite CLI** is a professional-grade command-line interface tool for sports bettors. It automates the end-to-end workflow of tracking handicappers ("cappers"):
1.  **Scraping**: Aggregates betting picks from Telegram channels and Twitter/X accounts.
2.  **OCR & Vision**: Uses a hybrid `RapidOCR` + `Broader Vision AI` pipeline to digitize betting slips.
3.  **AI Parsing**: Extracts structured data (Pick, Odds, Units, Sport, Bet Type) using a "Council" of LLMs (Gemini, Groq, Mistral).
4.  **Consensus & Validation**: Applies a **"Consensus Engine"** where multiple models vote on ambiguous picks, and a **"Semantic Auditor"** to flag logic errors (e.g., mismatched bet types).
5.  **Grading**: Validates picks against real-time ESPN scores using a V3 Grading Engine that supports Props, Parlays, and complex derivates (F5, 1H).
6.  **Storage**: Uploads validated, graded picks to a Supabase PostgreSQL database.

**Core Value**: High-throughput, "set-it-and-forget-it" automation with <1% error rates thanks to multi-stage AI verification.

## Tech Stack
*   **Language**: Python 3.10+
*   **Core Libraries**:
    *   **Network**: `asyncio`, `aiohttp` (Async requests), `urllib` (Fallback/Groq), `telethon` (Telegram MTProto), `twikit` (Twitter/X).
    *   **Browser**: `playwright` (Headless rendering for complex pages).
    *   **Vision/OCR**: `rapidocr-onnxruntime` (Local fast OCR), `Pillow`.
    *   **Data/Math**: `numpy`, `scikit-learn` (Clustering), `pydantic` (Data Validation).
    *   **Database**: `supabase` (PostgreSQL interface).
*   **AI Ecosystem**:
    *   **Providers**: OpenRouter, Gemini, Groq, Mistral.
    *   **Strategy**: "Round Robin" or "Groq Priority" pooling.
    *   **Consensus**: Majority voting system for low-confidence picks.
*   **DevOps**: `python-dotenv` (Config), `ruff` (Linting), `mypy` (Typing).

## Project Structure
```text
/
├── benchmark/              # "Golden Set" validation & performance measuring tools
├── data/                   # Runtime state (cache.db, logs, debug_, images) - .gitignored
├── docs/                   # subsystem documentation (OCR.md, GRADING.md)
├── src/                    # Application Source Code
│   ├── clients/            # External API clients (discord, telegram, twitter)
│   ├── enrichment/         # Pick data enrichment (odds backfilling, game matching)
│   ├── grading/            # V3 Grading Engine (ESPN scraping, parsing, matching)
│   │   ├── engine.py       # Main grading logic & bet type handlers
│   │   ├── matcher.py      # Fuzzy team matching logic
│   │   └── constants.py    # League/Team/Stat mappings
│   ├── parsers/            # Raw text/HTML parsers
│   ├── parsing/            # AI Parsing logic & prompt schemas
│   ├── prompts/            # LLM Prompt templates (system prompts, few-shot examples)
│   ├── extraction_pipeline.py  # MAIN ORCHESTRATOR: Scrape -> OCR -> AI -> Validate
│   ├── consensus_engine.py     # "The Council" voting logic
│   ├── provider_pool.py        # AI Provider load balancing (Urllib/Groq focus)
│   ├── rules_based_extractor.py # Regex/Heuristic extraction (Pass 1)
│   ├── models.py           # Pydantic data models (BetPick, TelegramMessage)
│   └── utils.py            # Shared helpers (logging, string cleaning)
├── tools/                  # Maintainance scripts (golden set creation, aliases)
├── cli_tool.py             # CLI Entry Point
└── requirements.txt        # Dependency manifest
```

## Key Architecture & Patterns
1.  **Pipeline Architecture**:
    *   Input: Telegram/Twitter Messages ->
    *   **Pass 1**: Rule-Based Extractor (Regex) ->
    *   **Pass 2**: AI Extractor (LLM) for complex/missed items ->
    *   **Pass 3**: "The Auditor" (Semantic Validation) ->
    *   **Pass 4**: "Consensus Council" (Multi-model voting for flagged items) ->
    *   Output: Structured, enriched JSON.
2.  **Grading Engine V3**:
    *   **Detection**: Automatically detects bet types (Spread, ML, Total, Prop, Parlay).
    *   **Suspicion System**: If rule-based grading fails or looks "suspicious" (e.g., mismatching word counts), it triggers an **AI Fallback** to resolve the bet type.
    *   **Caching**: aggressive SQLite and in-memory caching for ESPN score data to minimize API calls.
3.  **Hybrid Provider Pool**:
    *   Currently emphasizes `urllib`-based clients for Groq to minimize dependency conflicts, with fallbacks to `requests`/`aiohttp` for other providers.
4.  **Data Models**:
    *   Strict `Pydantic` validation ensures data integrity before it ever reaches the database.

## Development Conventions
*   **Type Hinting**: Fully typed codebase. `mypy` compatible.
*   **Linting**: Strict `ruff` rules (max-line-length 120).
*   **Error Handling**: "Fail-safe" processing. One bad message should never crash the batch.
*   **Environment**: Secrets managed via `.env`. See `.env.example`.
*   **Testing**: Heavy reliance on "Golden Set" benchmarking (`benchmark/`) rather than traditional unit tests for AI logic.

## Setup & Run Instructions
1.  **Install Application**:
    ```bash
    git clone <repo_url>
    pip install -r requirements.txt
    playwright install chromium
    ```
2.  **Configure Environment**:
    *   Copy `.env.example` to `.env`.
    *   **Required**: `API_ID`, `API_HASH` (Telegram), `SUPABASE_URL`, `SUPABASE_KEY`, `OPENROUTER_API_KEY` (or Groq/Gemini keys).
    *   **Optional**: `ENABLE_CONSENSUS=true` (to enable multi-model voting).
3.  **Run**:
    ```bash
    python cli_tool.py          # Run standard extraction
    python cli_tool.py --dry-run # Run without database upload (test mode)
    ```
4.  **Benchmarking**:
    ```bash
    python benchmark/benchmark_performance.py # Run speed/accuracy tests
    ```

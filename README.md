# CapperSuite CLI v4.6.1

![Version](https://img.shields.io/badge/version-4.6.1-blue.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-green.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

A professional-grade CLI tool for sports bettors. Scrapes, parses, **grades**, and uploads betting picks from Telegram channels and Twitter accounts using **Vision AI**, **Large Language Models**, and **ESPN real-time scores**.

```
$ python cli_tool.py --dry-run

==================================================
   TELEGRAM & TWITTER SCRAPER CLI   
==================================================
Fetching Telegram messages...
Fetched 47 messages.
Processing 23 images...
OCR Complete.
Selected 18 likely pick messages.
Extracted 42 picks.
Grading picks against ESPN scores...
Fetched 494 game scores
Grading complete: 28 Wins, 12 Losses, 2 Pending

CAPPER               | SPORT      | PICK                                | ODDS  | RESULT  
-----------------------------------------------------------------------------------------------
SharpAction          | NBA        | Lakers -4.5                         | -110  | Win     
VegasInsider         | NFL        | Chiefs ML                           | -150  | Pending 
CapperKing           | NCAAB      | Kansas +3.5                         | -105  | Loss    
...
```

---

## Quick Start

```bash
# Install
git clone https://github.com/Ducky705/Telegram-Scraper.git
cd Telegram-Scraper
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your API keys (see Environment Variables below)

# Run
python cli_tool.py
```

All data, logs, and sessions are stored in the `data/` directory.

---

## Features

### 1. Multi-Source Aggregation
- **Telegram** - Scrapes configured channels for betting picks
- **Twitter** - Fetches tweets from followed cappers
- **Deduplication** - Merges cross-posted content automatically

### 2. Smart OCR Pipeline
```
Image → RapidOCR (fast, local) → Vision AI (fallback) → Structured Text
```
- **RapidOCR** runs first (~1.2s avg, 93% confidence). Deep learning based.
- Vision AI races multiple providers in parallel for complex images.
- Automatic image preprocessing optimized for betting slips.

### 3. AI-Powered Parsing
```
Text → Classification → LLM Parser → Structured JSON
```
- Auto-filters promotional posts, recaps, and data dumps.
- Hybrid provider pool: fast models first, strong fallback.
- Two-pass verification for parsing confidence.
- **Ultra-compact prompts** - 67% token reduction for faster batches.

### 4. Automated Grading
```
Pick + ESPN Scores → Grading Engine V3 → Win/Loss/Push/Pending
```
- **Real-time ESPN data** - Fetches scores from 57 endpoints in parallel
- **Smart team matching** - Uses 500+ team aliases for accurate matching
- **All bet types** - Spreads, Moneylines, Totals, Player Props, Parlays
- **3x faster** than legacy grader with higher accuracy
- **Persistent caching** - SQLite cache for scores/boxscores (24hr/7day TTL)
- **Connection pooling** - Reusable TCP connections for faster API calls
- **League-aware fetching** - Only fetches leagues present in picks (up to 15x faster)

---

## 📚 Documentation

Detailed documentation for each subsystem:

- **[Architecture Overview](docs/ARCHITECTURE.md)** - System design and data flow.
- **[Grading System](docs/GRADING.md)** - V3 Engine, rules, and logic.
- **[OCR Pipeline](docs/OCR.md)** - RapidOCR and Vision AI cascade.
- **[Prompt System](docs/PROMPTS.md)** - Token optimization and compact schema.
- **[AI Providers](docs/PROVIDERS.md)** - Parallel processing and rate limits.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLI PIPELINE                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ TELEGRAM │    │ TWITTER  │    │  DEDUPE  │    │  AUTO    │    │   OCR    │   │
│  │ SCRAPER  │──▶│ SCRAPER   │──▶│  MERGE   │──▶│ CLASSIFY │──▶ │ CASCADE  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                                                       │         │
│                                                                       ▼         │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ SUPABASE │◀──│  OUTPUT  │◀───│  GRADER  │◀──│ VALIDATE │ ◀──│  PARSE   │   │
│  │  UPLOAD  │    │   JSON   │    │    V3    │    │ 2-PASS   │    │  HYBRID  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                        │                                        │
│                                        ▼                                        │
│                               ┌──────────────┐                                  │
│                               │  ESPN SCORES │                                  │
│                               │  (57 APIs)   │                                  │
│                               └──────────────┘                                  │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Changelog

### v4.6.1 (January 23, 2026)
- **Polish**: Final documentation, diagram, and arrow direction fixes.
- **Refinement**: Cleaned up root directory and optimized import paths.

### v4.6.0 (January 23, 2026)
- **Performance Milestone**: Introduced Persistent SQLite Caching.
- **Grader Speed**: 6.3x faster grading via connection pooling and league-aware fetching.
- **Reliability**: Connection pooling (20-connection pool) for ESPN API calls.

### v4.5.0 (January 23, 2026)
- **Architecture**: Full project restructuring.
- **Organization**: Consolidated runtime data (logs, cache, images) into `data/`.
- **Modularity**: Moved documentation to `docs/` and utilities to `tools/`.

### v4.4.0 (January 22, 2026)
- **Efficiency**: Implemented Compact Prompt Schema.
- **Token Reduction**: 67% reduction in token usage per message.
- **Decoder**: Automatic expansion of compact AI responses to full field names.

### v4.3.0 (January 22, 2026)
- **Throughput**: Rate limit optimization for maximum speed.
- **Concurrency**: Increased total concurrent workers to 25 (+79% improvement).
- **Strategy**: Groq-first routing strategy for 0.9s latencies.

### v4.2.0 (January 22, 2026)
- **Grading Engine V3**: Complete rewrite of the grading logic.
- **Accuracy**: Eliminated false positives and improved team matching (500+ aliases).
- **Benchmarking**: Added comprehensive grading benchmark tools.

### v4.1.1 (January 21, 2026)
- **Market Support**: Added strict format enforcement for Tennis and Parlay markets.
- **Logic**: Improved Period/Half detection logic for sports betting.

### v4.1.0 (January 21, 2026)
- **Vision Update**: Integration of RapidOCR (Deep Learning Engine).
- **Reliability**: 93% avg confidence vs 60% with legacy Tesseract.

### v4.0.0 (January 21, 2026)
- **THE CLI EVOLUTION**: Removed GUI entirely.
- **Pivot**: Transitioned to professional-grade CLI-only architecture.
- **Performance**: High-concurrency focus for power users.

### v3.1.1 (January 18, 2026)
- **Confidence**: Added Two-Pass Verification System ('Chimera' logic).
- **Validation**: Conflict resolution for multi-provider routing.

### v3.1.0 (January 18, 2026)
- **Peak GUI Milestone**: Final major update for the Desktop interface.
- **OCR**: Parallel Vision AI OCR cascade implemented.

### v3.0.0 (January 13, 2026)
- **AI Core**: First implementation of AI Auto-Classification.
- **Filtering**: Automated detection of PROMO, RECAP, and NOISE messages.

### v2.0.0 (January 13, 2026)
- **Intelligence**: Introduced Grading Engine V2 with ESPN Integration.
- **Leagues**: Added support for 26+ sports leagues.

### v1.1.0 (January 5, 2026)
- **Intelligence Hub**: Advanced OCR preprocessing and benchmarking tools.

### v1.0.1 (January 3, 2026)
- **Patch**: Silent auto-update and API retry logic.

### v1.0.0 (December 20, 2025)
- **FIRST STABLE RELEASE**: Standalone Desktop GUI (Win/Mac).

### v0.2.0 (December 8, 2025)
- **Visibility**: Added comprehensive Mermaid architecture diagrams.

### v0.1.0 (December 8, 2025)
- **Foundation**: Initial repository cleanup and professional structure.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

**Built with AI. Optimized for sports bettors.**

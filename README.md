# CapperSuite CLI v3.6

![Version](https://img.shields.io/badge/version-3.6.0-blue.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-green.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

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

### 4. Prompt Optimization (NEW in v3.6)
```
Before: {"capper_name": "King", "league": "NBA", "type": "Player Prop", ...}
After:  {"c": "King", "l": "NBA", "t": "PP", ...}
```
- **1-char JSON keys** reduce output tokens by 50%
- **Type abbreviations** (ML, SP, PP, PL, etc.) save additional tokens
- **Centralized prompt module** (`src/prompts/`) for maintainability
- **Automatic decoder** expands compact responses to full field names
- **Backward compatible** - handles both old and new formats

### 4. Automated Grading (NEW in v3.3)
```
Pick + ESPN Scores → Grading Engine V3 → Win/Loss/Push/Pending
```
- **Real-time ESPN data** - Fetches scores from 57 endpoints in parallel
- **Smart team matching** - Uses 500+ team aliases for accurate matching
- **All bet types** - Spreads, Moneylines, Totals, Player Props, Parlays
- **3x faster** than legacy grader with higher accuracy

### 5. Structured Output
```json
{
  "capper_name": "SharpAction",
  "league": "NBA",
  "type": "spread",
  "pick": "Lakers -4.5",
  "odds": "-110",
  "units": 1.0,
  "result": "Win",
  "score_summary": "Los Angeles Lakers 115 (+4.5=119.5) vs Phoenix Suns 112"
}
```

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

### OCR Cascade
| Stage | Provider | Time | Confidence |
|-------|----------|------|------------|
| 1. Fast | **RapidOCR** (local, ONNX) | ~1.2s | 93% |
| 2. Vision | Mistral Pixtral Large | ~16s | 100% |
| 3. Fallback | OpenRouter Gemma 3 27B | ~16s | 100% |

### Parser Pool - MAXIMUM SPEED Configuration (v3.5)

| Tier | Provider | Model | Concurrent | RPM | TPM | Latency |
|------|----------|-------|------------|-----|-----|---------|
| **PRIMARY** | **Groq** | llama-3.3-70b-versatile | **16** | 1000 | 300K | 1.0s |
| SECONDARY | Mistral | codestral-latest | 4 | 60 | 500K | 1.6s |
| TERTIARY | Gemini | gemini-2.5-flash-lite | 3 | 15 | 250K | 5.4s |
| OVERFLOW | Cerebras | llama3.1-8b | 2 | 30 | 60K | 0.9s |
| FALLBACK | OpenRouter | deepseek-r1 | 0 | N/A | N/A | 3-120s |

**Total: 25 concurrent workers (was 14 = +79% improvement)**

---

## Prompt Optimization (v3.6)

The prompt system has been completely rewritten for **maximum token efficiency**. This enables larger batch sizes and faster processing.

### Compact Schema

| Compact Key | Full Name | Example |
|-------------|-----------|---------|
| `i` | message_id | `123` |
| `c` | capper_name | `"KingCap"` |
| `l` | league | `"NBA"` |
| `t` | type | `"PP"` (Player Prop) |
| `p` | pick | `"LeBron: Pts O 25.5"` |
| `o` | odds | `-110` |
| `u` | units | `1.0` |

### Type Abbreviations

| Abbrev | Full Type |
|--------|-----------|
| `ML` | Moneyline |
| `SP` | Spread |
| `TL` | Total |
| `PP` | Player Prop |
| `TP` | Team Prop |
| `GP` | Game Prop |
| `PD` | Period |
| `PL` | Parlay |
| `TS` | Teaser |
| `FT` | Future |
| `UK` | Unknown |

### Token Savings

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Output tokens per pick | ~50 | ~25 | **50% reduction** |
| Main extraction prompt | ~1200 tokens | ~400 tokens | **67% reduction** |
| OCR batch prompt | ~100 tokens | ~30 tokens | **70% reduction** |

### Usage

The decoder automatically expands compact responses:

```python
from src.prompts.decoder import normalize_response, expand_picks_list

# AI returns compact format
response = '{"picks":[{"i":1,"c":"Cap","l":"NBA","t":"SP","p":"Lakers -5","o":-110}]}'

# Decoder expands to full field names
picks = normalize_response(response)
# Result: [{"message_id": 1, "capper_name": "Cap", "league": "NBA", "type": "Spread", ...}]
```

### Module Structure

```
src/prompts/
├── __init__.py      # Module exports
├── core.py          # Schema definitions, prompt builders
└── decoder.py       # Response expansion utilities
```

---

## Environment Variables

```env
# ─────────────────────────────────────────────────
# REQUIRED - Telegram API (get from my.telegram.org)
# ─────────────────────────────────────────────────
API_ID=your_api_id
API_HASH=your_api_hash

# ─────────────────────────────────────────────────
# RECOMMENDED - AI Providers
# ─────────────────────────────────────────────────
GROQ_TOKEN=your_key          # BEST: Fastest + 100% accuracy (0.9s)
MISTRAL_TOKEN=your_key       # Best parser + vision (1.6s, 100% accuracy)
CEREBRAS_TOKEN=your_key      # Fast parser (0.9s, 93.4% accuracy)
GEMINI_TOKEN=your_key        # Direct Gemini API (100% accuracy, 5.4s)

# ─────────────────────────────────────────────────
# OPTIONAL
# ─────────────────────────────────────────────────
OPENROUTER_API_KEY=your_key  # Slow fallback (22s latency)

# Twitter (if using Twitter scraping)
TWITTER_USERNAME=your_user
TWITTER_EMAIL=your_email
TWITTER_PASSWORD=your_pass
```

---

## CLI Usage

### Basic Run
```bash
# Scrape yesterday's picks (default) - with Supabase upload
python cli_tool.py

# Dry run - scrape, parse, grade but DON'T upload to Supabase
python cli_tool.py --dry-run
```

### Output Files
| File | Description |
|------|-------------|
| `picks_YYYY-MM-DD.json` | Structured pick data with grades |
| `cli_scraper.log` | Debug logs |
| `cache/ocr_hashes/` | OCR result cache |

### Sample Output
```json
[
  {
    "message_id": 12345,
    "capper_name": "SharpAction",
    "league": "NBA",
    "type": "spread",
    "pick": "Lakers -4.5",
    "odds": "-110",
    "units": 1.0,
    "result": "Win",
    "score_summary": "Los Angeles Lakers 115 (+4.5=119.5) vs Phoenix Suns 112"
  }
]
```

---

## Benchmarks

### Local OCR - RapidOCR (January 21, 2026)

| Metric | Value |
|--------|-------|
| **Engine** | RapidOCR (ONNX Runtime) |
| **Avg Time** | 1,217ms |
| **Avg Confidence** | 93% |
| **Min/Max Time** | 483ms / 2,313ms |
| **Avg Text Length** | 261 chars |

RapidOCR replaces Tesseract with a deep learning model (PaddleOCR via ONNX).
It handles dark backgrounds, stylized fonts, and complex layouts natively.

### Vision Models (January 21, 2026)

| Model | Provider | Avg Time | Picks/Img | Success | Status |
|-------|----------|----------|-----------|---------|--------|
| **Mistral Pixtral Large** | Mistral | 16.2s | 4.2 | 100% | **PRIMARY** |
| Gemma 3 27B | OpenRouter | 16.5s | 4.4 | 100% | FALLBACK |
| Gemma 3 12B | OpenRouter | 19.2s | 4.2 | 100% | FALLBACK |
| Gemini 2.0 Flash | OpenRouter | 58s | 2.2 | 100% | RATE-LIMITED |
| All Groq models | Groq | - | 0 | 0% | NO VISION |
| All Cerebras models | Cerebras | - | 0 | 0% | NO VISION |

### Parser Models (January 22, 2026) - Golden Set Benchmark

**Comprehensive benchmark across 33 free models, 5 providers, tested against 61-65 picks from 20 messages:**

**21 models successfully benchmarked (12 models failed due to errors/timeout):**

| Rank | Provider | Model | F1 | Precision | Recall | Latency | Notes |
|------|----------|-------|-----|-----------|--------|---------|-------|
| 1 | **Groq** | **llama-3.1-8b-instant** | **100%** | 100% | 100% | **930ms** | **FASTEST + BEST** |
| 2 | Groq | llama-3.3-70b-versatile | **100%** | 100% | 100% | 1,019ms | |
| 3 | Groq | openai/gpt-oss-20b | **100%** | 100% | 100% | 1,598ms | |
| 4 | **Mistral** | **codestral-latest** | **100%** | 100% | 100% | 1,646ms | Best Mistral |
| 5 | Groq | openai/gpt-oss-120b | **100%** | 100% | 100% | 2,371ms | |
| 6 | Mistral | mistral-large-2411 | **100%** | 100% | 100% | 4,735ms | |
| 7 | **Gemini** | **gemini-2.5-flash-lite** | **100%** | 100% | 100% | 5,451ms | Best Gemini |
| 8 | Gemini | gemini-2.5-flash | **100%** | 100% | 100% | 11,049ms | |
| 9 | OpenRouter | deepseek/deepseek-r1-0528:free | **100%** | 100% | 100% | ~3-60s* | Variable* |
| 10 | OpenRouter | meta-llama/llama-3.3-70b-instruct:free | **100%** | 100% | 100% | ~1.4s* | Fast on OR |
| 11 | OpenRouter | nvidia/nemotron-3-nano-30b-a3b:free | **100%** | 100% | 100% | ~1s* | Fast on OR |
| 12 | OpenRouter | arcee-ai/trinity-mini:free | **100%** | 100% | 100% | ~1.2s* | Fast on OR |
| 13 | Mistral | mistral-large-latest | 95.1% | 95.1% | 95.1% | 4,397ms | |
| 14 | Mistral | mistral-saba-2502 | 93.5% | 92.1% | 95.1% | 3,225ms | |
| 15 | Mistral | mistral-small-latest | 93.5% | 92.1% | 95.1% | 3,694ms | |
| 16 | Cerebras | llama3.1-8b | 93.4% | 93.4% | 93.4% | 934ms | Fast |
| 17 | Mistral | mistral-small-2501 | 92.8% | 90.6% | 95.1% | 1,244ms | |
| 18 | Cerebras | qwen-3-32b | 92.8% | 90.6% | 95.1% | 2,793ms | |
| 19 | Cerebras | llama-3.3-70b | 92.1% | 89.2% | 95.1% | 897ms | 2nd fastest |
| 20 | Cerebras | gpt-oss-120b | 89.8% | 86.4% | 93.4% | 1,337ms | |
| 21 | Mistral | codestral-2501 | 88.1% | 100% | 78.7% | 1,476ms | High precision |

**Provider Status:**
- ✅ **Groq**: Working excellent, 4 models tested, **ALL 100% F1**, fastest overall (930-2,371ms)
- ✅ **Mistral**: Working excellent, 7 models tested, best for variety (1.2-4.7s)
- ✅ **Gemini Direct**: Working, 2 models tested (5-11s)
- ✅ **Cerebras**: Working fast, 4 models tested (900-2,800ms)
- ⚠️ **OpenRouter**: **Extremely slow** (3-120s per request), not recommended for production
  - Fast OR models (~1s) are available but routing is inconsistent
  - DeepSeek R1 takes 3-60s (reasoning models are slow)
  - Not included in parallel processor due to unpredictable latency

**Key Findings:**
- **Groq llama-3.1-8b-instant** is **RECOMMENDED** - 100% accuracy with only 930ms latency
- All Groq models achieve 100% F1 - Groq is now the best provider
- **Mistral codestral-latest** is best Mistral option (100% F1, 1.6s)
- Cerebras is fast but accuracy is lower (93.4%) than Groq/Mistral
- OpenRouter has some fast models (~1s) but routing is unpredictable; not suitable for production
- **Gemini 3 Flash**: Not yet available in API (checked 2026-01-22) - up to 2.5 only

### Parallel Batch Processing Architecture (v3.5)

**MAXIMUM SPEED rate-limit-aware load balancing:**

| Provider | RPM | TPM | Concurrent | Min Delay | Model | Priority |
|----------|-----|-----|------------|-----------|-------|----------|
| **Groq** | **1000** | 300K | **16** | 60ms | llama-3.3-70b-versatile | PRIMARY |
| Mistral | 60 | 500K | 4 | 1.0s | codestral-latest | SECONDARY |
| Gemini | 15 | 250K | 3 | 4.0s | gemini-2.5-flash-lite | TERTIARY |
| Cerebras | 30 | 60K | 2 | 2.0s | llama3.1-8b | OVERFLOW |
| OpenRouter | N/A | N/A | 0 | N/A | deepseek-r1 | FALLBACK ONLY |

```
BATCHES:    [B1] [B2] [B3] ... [B16] [B17] [B18] [B19] [B20] [B21] [B22] [B23] [B24] [B25]
               ↓    ↓    ↓  ...   ↓     ↓     ↓     ↓     ↓     ↓     ↓     ↓     ↓     ↓
WORKERS:   [GRQ][GRQ][GRQ]...[GRQ] [MIS] [MIS] [MIS] [MIS] [GEM] [GEM] [GEM] [CER] [CER]
           └──────── 16 Groq workers (64%) ─────────┘└─ 4 Mistral ─┘└─ 3 Gem ─┘└─ 2 ─┘
```

**Strategy:**
- **Groq handles 64% of load** (16 concurrent workers, 1000 RPM)
- Mistral handles 16% (4 workers, can batch 10 msgs/call for 500K TPM)
- Gemini handles 12% (3 workers)
- Cerebras handles 8% (2 workers)
- **OpenRouter is FALLBACK ONLY** (3-120s latency, not recommended)
- Rate limiters prevent 429 errors
- Automatic fallback on failures

### Run Your Own Benchmark
```bash
# Full benchmark (all 33 models)
python tools/benchmark_all_models.py --limit 20

# Quick test (specific providers)
python tools/benchmark_all_models.py --limit 10 --providers cerebras mistral

# Retry failed models only
python tools/benchmark_all_models.py --retry-failed --limit 20
```


### Grading Engine V3 (January 22, 2026)

| Metric | Old Grader | New Grader V3 | Improvement |
|--------|------------|---------------|-------------|
| **Processing Time** | 40.6s | 11.3s | **3.6x faster** |
| **Coverage** | 90.5% | 85.1% | More accurate* |
| **Architecture** | Monolithic | Modular | Maintainable |
| **False Positives** | Yes | No | **Eliminated** |

*The old grader had higher "coverage" due to false positive matches (e.g., matching "Kent State" to "Iowa State"). The new grader correctly returns PENDING when games don't exist.

**Supported Bet Types:**
- Spreads, Moneylines, Totals
- Player Props (with boxscore lookup)
- Parlays & Teasers (recursive leg grading)
- Period bets (1H, 1Q, F5, etc.)

**Data Sources:**
- ESPN API (57 parallel endpoints)
- All major leagues: NFL, NBA, NHL, MLB, NCAAF, NCAAB, Soccer, Tennis, UFC, Golf

### Run Benchmarks
```bash
# Vision benchmark
python -m benchmark.ocr_benchmark --limit 10 --parallel

# Parser benchmark
python -m benchmark.parser_benchmark --samples 5
```

---

## Project Structure

```
├── cli_tool.py              # Main CLI entry point
├── config.py                # Configuration
├── src/
│   ├── telegram_client.py   # Telegram scraper
│   ├── twitter_client.py    # Twitter scraper
│   ├── deduplicator.py      # Cross-source deduplication
│   ├── auto_processor.py    # Smart message classification
│   ├── ocr_engine.py        # RapidOCR engine wrapper
│   ├── ocr_cascade.py       # Vision AI OCR cascade
│   ├── ocr_handler.py       # OCR orchestration
│   ├── ocr_preprocessing.py # Image preprocessing (RapidOCR-optimized)
│   ├── ocr_validator.py     # OCR quality validation
│   ├── provider_pool.py     # Hybrid LLM provider pool
│   ├── prompt_builder.py    # AI prompt generation (optimized v3.6)
│   ├── prompts/             # Prompt Optimization Module (v3.6)
│   │   ├── __init__.py      # Module exports
│   │   ├── core.py          # Compact schema, prompt builders
│   │   └── decoder.py       # Response expansion utilities
│   ├── two_pass_verifier.py # Parsing verification
│   ├── grader.py            # Grading wrapper (uses V3)
│   ├── grading/             # Grading Engine V3
│   │   ├── engine.py        # Core grading engine
│   │   ├── parser.py        # Pick text parser
│   │   ├── matcher.py       # Team/player matching
│   │   ├── schema.py        # Data structures
│   │   ├── constants.py     # League mappings
│   │   └── loader.py        # ESPN data loader
│   ├── score_fetcher.py     # ESPN score fetcher
│   ├── team_aliases.py      # 500+ team name aliases
│   ├── supabase_client.py   # Supabase database client
│   ├── cerebras_client.py   # Cerebras API client
│   ├── mistral_client.py    # Mistral API client
│   ├── openrouter_client.py # OpenRouter API client
│   ├── groq_client.py       # Groq API client
│   └── gemini_client.py     # Gemini API client
├── scripts/
│   └── regrade_picks.py     # Bulk regrade Supabase picks
├── benchmark/
│   ├── ocr_benchmark.py     # Vision model benchmark
│   ├── parser_benchmark.py  # Parser model benchmark
│   ├── runners/
│   │   ├── grading_benchmark.py    # Grading parser test
│   │   └── grading_comparison.py   # Old vs new grader
│   └── reports/             # Benchmark results
└── requirements.txt         # Dependencies
```

---

## How It Works

### 1. Fetch Messages
```python
# Telegram
tg = TelegramManager()
messages = await tg.fetch_messages([channel_id], target_date)

# Twitter  
tw = TwitterManager()
tweets = await tw.fetch_tweets(target_date)
```

### 2. Deduplicate
```python
from src.deduplicator import Deduplicator
unique = Deduplicator.merge_messages(all_messages)
```

### 3. OCR Images
```python
from src.ocr_handler import extract_text_batch
results = extract_text_batch(image_paths)
```

### 4. Classify Messages
```python
from src.auto_processor import auto_select_messages
selected = auto_select_messages(messages, use_ai=True)
# Filters: PROMO, RECAP, DATA, NOISE
# Keeps: PICK, UNKNOWN
```

### 5. Parse Picks (Parallel Multi-Provider)
```python
from src.parallel_batch_processor import parallel_processor

# Split messages into batches (10 msgs each)
batches = [messages[i:i+10] for i in range(0, len(messages), 10)]

# Process in parallel across Cerebras, Mistral, Gemini
results = parallel_processor.process_batches(batches)
# Dynamic load balancing: next batch goes to first available provider
# Throughput: ~3x faster than sequential (3 concurrent workers)
```

### 6. Grade Picks
```python
from src.grader import grade_picks
from src.score_fetcher import fetch_scores_for_date

scores = fetch_scores_for_date("2026-01-20")
graded = grade_picks(picks, scores)
# Each pick now has: result="Win"/"Loss"/"Push"/"Pending", score_summary="..."
```

### 7. Verify & Upload
```python
from src.two_pass_verifier import TwoPassVerifier
TwoPassVerifier.verify_parsing_result(picks)

from src.supabase_client import upload_picks
upload_picks(graded, target_date)
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `GROQ_TOKEN not set` | Add token to `.env` file (get from console.groq.com) |
| `CEREBRAS_TOKEN not set` | Add token to `.env` file |
| `Rate limited (429)` | Wait 1-2 minutes, reduce batch size |
| `RapidOCR not available` | Install: `pip install rapidocr-onnxruntime` |
| `No picks extracted` | Check if messages contain valid betting content |
| `OpenRouter slow (22s+)` | Use Groq/Mistral/Cerebras/Gemini instead (0.9s-5.4s) |

### Debug Mode
```bash
# Enable verbose logging
python cli_tool.py 2>&1 | tee debug.log
```

---

## Performance Summary

| Metric | Value |
|--------|-------|
| Local OCR Accuracy | 93% (RapidOCR) |
| Vision AI Accuracy | 100% (Mistral Pixtral) |
| Parsing Accuracy | 100% (Groq llama-3.3-70b-versatile) |
| **Best Parse Time** | **870ms** (Groq + Compact Prompts) |
| **Parsing F1 Score** | **75.0%** (Full Pipeline Benchmark) |
| **Max Throughput** | **25 concurrent workers** (16 Groq + 4 Mistral + 3 Gemini + 2 Cerebras) |
| **Groq Rate Limit** | 1000 RPM, 300K TPM (16 concurrent) |
| **Mistral Batching** | 10 msgs/call (500K TPM) |
| **Grading Speed** | 11.3s / 74 picks |
| Avg Local OCR Time | 1.2s (RapidOCR) |
| Avg Vision OCR Time | 16.2s (Mistral Pixtral Large) |
| OpenRouter | FALLBACK ONLY (3-120s latency) |

---

## Changelog

### v3.6.0 (January 22, 2026)
- **Prompt Optimization** - Maximum token efficiency for AI prompts
  - Created `src/prompts/` module with centralized prompt management
  - **1-char JSON keys** reduce output tokens by 50% (`c` instead of `capper_name`)
  - **Type abbreviations** save tokens (`PP` instead of `Player Prop`)
  - Main extraction prompt reduced from ~1200 to ~400 tokens (**67% reduction**)
  - OCR batch prompt reduced from ~100 to ~30 tokens (**70% reduction**)
- **Automatic Decoder** - Expands compact AI responses to full field names
  - `normalize_response()` handles JSON extraction + expansion
  - `expand_picks_list()` expands list of compact picks
  - Backward compatible with old 2-char key format
- **Updated Scrapers** - All scrapers now use the decoder
  - `cli_tool.py`, `run_discord_scraper.py`, `run_twitter_scraper.py`
  - Downstream code receives full field names (no changes required)
- **Compressed Secondary Prompts**
  - Vision one-shot parsing prompt optimized
  - Benchmark parsing prompt optimized
  - Golden set auditor prompt optimized

### v3.5.0 (January 22, 2026)
- **Rate Limit Optimization** - Maximum speed configuration
  - Increased total concurrent workers from 14 to **25** (+79% throughput)
  - Replaced all `Lock()` with `Semaphore()` for true parallel processing
  - Provider concurrency: Groq=16, Mistral=4, Gemini=3, Cerebras=2
- **Groq-First Strategy** - Routes 80%+ of requests to fastest provider
  - Changed default model to `llama-3.3-70b-versatile` (was `llama-3.1-8b-instant`)
  - 16 concurrent requests (was 1 due to Lock)
  - 1000 RPM, 300K TPM capacity
- **Mistral Batching** - Bundle 10 messages per API call
  - Leverages 500K TPM limit for batch processing
  - 4 concurrent connections with message bundling
- **OpenRouter Demoted** - Marked as FALLBACK ONLY
  - 3-120s latency makes it unsuitable for primary use
  - Only triggered when ALL fast providers fail

### v3.4.0 (January 22, 2026)
- **Parallel Batch Processing**
  - Implemented dynamic load balancer across 5 providers (Cerebras, Groq, Mistral, Gemini, OpenRouter)
  - Processes batches in parallel (1 per provider) to bypass free-tier rate limits
  - Automatically routes tasks to the fastest available provider
- **Comprehensive Benchmarking Tool**
  - Added `tools/benchmark_all_models.py` to test 25+ free models against the golden set
  - Measures Precision, Recall, F1, and Latency for every model
  - Outputs detailed JSON reports to `benchmark/reports/`
- **Gemini Text Support**
  - Added text completion support to Gemini client (previously vision-only)

### v3.3.0 (January 22, 2026)

- **Grading Engine V3** - Complete rewrite of pick grading system
  - 3.6x faster than legacy grader (11.3s vs 40.6s for 74 picks)
  - Modular architecture: `src/grading/` package
  - Eliminated false positive matches (old grader matched "Kent State" to "Iowa State")
  - Smart team matching with 500+ aliases
  - Support for all bet types: Spreads, Moneylines, Totals, Props, Parlays
- **CLI Integration** - Full pipeline now includes grading
  - Picks are graded against ESPN scores before output
  - Results shown in table: CAPPER | SPORT | PICK | ODDS | RESULT
  - `--dry-run` flag to skip Supabase upload
- **Supabase Upload** - Graded picks uploaded to database
  - Auto-creates new cappers
  - Maps leagues and bet types to IDs
  - Stores result and score_summary
- **Bulk Regrade Script** - `scripts/regrade_picks.py`
  - Regrades historical picks in Supabase
  - Pagination for >1000 picks
  - Dry-run mode for preview

### v3.2.1 (January 21, 2026)
- **Strict Formatting Enforcement** - Prompt builder now rigorously adheres to `pick_format.md`
  - Added specific support for Tennis markets (Set/Game spreads, Set Winner)
  - Improved Period/Half detection logic
  - Enforced standardized Parlay/Teaser formatting
- **Bug Fixes** - Fixed import issues in CLI tool

### v3.2.0 (January 21, 2026)
- **RapidOCR replaces Tesseract** - Deep learning OCR (ONNX Runtime)
  - 93% avg confidence vs ~60% with Tesseract
  - 1.2s avg time (still much faster than Vision AI)
  - Handles dark backgrounds and stylized fonts natively
  - No binary install required (pure Python)
- **New preprocessing pipeline** - Optimized for deep learning OCR
  - Removed aggressive binarization (not needed for DL models)
  - CLAHE contrast enhancement instead of Otsu thresholding
  - Lanczos4 upscaling preserved
- Added `src/ocr_engine.py` - RapidOCR wrapper

### v3.1.1 (January 21, 2026)
- **Parser benchmark added** - Cerebras is fastest (901ms, 100% accuracy)
- **Vision benchmark updated** - 14 models tested across 4 providers
- **Mistral Pixtral Large** now primary vision model
- **Cerebras Llama 3.3 70B** now primary parser
- Confirmed Groq/Cerebras have NO vision support
- Added `parser_benchmark.py` script

### v3.1.0 (January 2026)
- Complete OCR cascade rewrite
- Added comprehensive vision model benchmarking
- Disabled Groq (broken) and Cerebras (text-only) for vision
- Improved error handling and fallback logic

### v3.0.0
- Initial Vision AI implementation
- Replaced legacy Tesseract-only OCR
- Added multi-provider support

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

**Built with AI. Optimized for sports bettors.**

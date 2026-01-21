# CapperSuite CLI v3.3

![Version](https://img.shields.io/badge/version-3.3.0-blue.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-green.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

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
│                              CLI PIPELINE                                        │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ TELEGRAM │    │ TWITTER  │    │  DEDUPE  │    │  AUTO    │    │   OCR    │   │
│  │ SCRAPER  │──▶│ SCRAPER  │───▶│  MERGE   │──▶│ CLASSIFY │──▶│ CASCADE  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                                                       │          │
│                                                                       ▼          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ SUPABASE │◀──│  OUTPUT  │◀───│  GRADER  │◀──│ VALIDATE │◀──│  PARSE   │   │
│  │  UPLOAD  │    │   JSON   │    │    V3    │    │ 2-PASS   │    │  HYBRID  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                        │                                         │
│                                        ▼                                         │
│                               ┌──────────────┐                                   │
│                               │  ESPN SCORES │                                   │
│                               │  (57 APIs)   │                                   │
│                               └──────────────┘                                   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### OCR Cascade
| Stage | Provider | Time | Confidence |
|-------|----------|------|------------|
| 1. Fast | **RapidOCR** (local, ONNX) | ~1.2s | 93% |
| 2. Vision | Mistral Pixtral Large | ~16s | 100% |
| 3. Fallback | OpenRouter Gemma 3 27B | ~16s | 100% |

### Parser Pool
| Tier | Provider | Model | Time | Accuracy |
|------|----------|-------|------|----------|
| Fast | Cerebras | Llama 3.3 70B | 0.9s | 100% |
| Fast | Mistral | Mistral Large | 1.9s | 100% |
| Strong | OpenRouter | DeepSeek R1 | 14s | 100% |

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
CEREBRAS_TOKEN=your_key      # Fastest parser (0.9s)
MISTRAL_TOKEN=your_key       # Best vision + good parser
OPENROUTER_API_KEY=your_key  # Strong fallback

# ─────────────────────────────────────────────────
# OPTIONAL
# ─────────────────────────────────────────────────
GROQ_TOKEN=your_key          # Currently has 403 issues
GEMINI_TOKEN=your_key        # Direct Gemini API

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

### Parser Models (January 21, 2026)

| Model | Provider | Avg Time | Accuracy | Status |
|-------|----------|----------|----------|--------|
| **Cerebras Llama 3.3 70B** | Cerebras | 901ms | 100% | **PRIMARY** |
| Mistral Large | Mistral | 1.9s | 100% | FAST |
| Devstral | OpenRouter | 4.1s | 100% | GOOD |
| DeepSeek R1 | OpenRouter | 14.5s | 100% | STRONG FALLBACK |

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
│   ├── prompt_builder.py    # AI prompt generation
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

### 5. Parse Picks
```python
from src.provider_pool import pooled_completion
result = pooled_completion(prompt)
# Tries: Cerebras → Groq → Mistral → OpenRouter (DeepSeek R1)
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
| `CEREBRAS_TOKEN not set` | Add token to `.env` file |
| `Groq 403 Access Denied` | Network/auth issue, use other providers |
| `Rate limited (429)` | Wait 1-2 minutes, reduce batch size |
| `RapidOCR not available` | Install: `pip install rapidocr-onnxruntime` |
| `No picks extracted` | Check if messages contain valid betting content |

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
| Vision AI Accuracy | 100% (Mistral) |
| Parsing Accuracy | 100% |
| **Grading Speed** | 11.3s / 74 picks |
| **Grading Coverage** | 85.1% |
| Avg Local OCR Time | 1.2s (RapidOCR) |
| Avg Vision OCR Time | 16.2s (Mistral) |
| Avg Parse Time | 0.9s (Cerebras) |
| Batch Throughput | 10 msgs/batch, 4 workers |

---

## Changelog

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

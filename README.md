# CapperSuite CLI v3.1

![Version](https://img.shields.io/badge/version-3.1.1-blue.svg) ![Python](https://img.shields.io/badge/python-3.10%2B-green.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

A professional-grade CLI tool for sports bettors. Scrapes, parses, and structures betting picks from Telegram channels and Twitter accounts using **Vision AI** and **Large Language Models**.

```
$ python cli_tool.py

==================================================
   TELEGRAM & TWITTER SCRAPER CLI   
==================================================
Fetching Telegram messages...
Fetched 47 messages.
Processing 23 images...
OCR Complete.
Selected 18 likely pick messages.
Extracted 42 picks.

CAPPER               | SPORT      | PICK                                     | ODDS  
-------------------------------------------------------------------------------------
SharpAction          | NBA        | Lakers -4.5                              | -110  
VegasInsider         | NFL        | Chiefs ML                                | -150  
CapperKing           | MLB        | Yankees/Red Sox OVER 8.5                 | -105  
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
Image → Tesseract (fast) → Vision AI (fallback) → Structured Text
```
- Tesseract runs first (~0.5s). If confidence >= 60%, done.
- Vision AI races multiple providers in parallel for reliability.
- Automatic image preprocessing for better accuracy.

### 3. AI-Powered Parsing
```
Text → Classification → LLM Parser → Structured JSON
```
- Auto-filters promotional posts, recaps, and data dumps.
- Hybrid provider pool: fast models first, strong fallback.
- Two-pass verification for parsing confidence.

### 4. Structured Output
```json
{
  "capper_name": "SharpAction",
  "league": "NBA",
  "type": "spread",
  "pick": "Lakers -4.5",
  "odds": "-110",
  "units": 1.0
}
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI PIPELINE                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ TELEGRAM │    │ TWITTER  │    │  DEDUPE  │    │  AUTO    │          │
│  │ SCRAPER  │───▶│ SCRAPER  │───▶│  MERGE   │───▶│ CLASSIFY │          │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│                                                        │                 │
│                                                        ▼                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  OUTPUT  │◀───│ VALIDATE │◀───│  PARSE   │◀───│   OCR    │          │
│  │   JSON   │    │ 2-PASS   │    │  HYBRID  │    │ CASCADE  │          │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### OCR Cascade
| Stage | Provider | Time | Success |
|-------|----------|------|---------|
| 1. Fast | Tesseract (local) | ~0.5s | 60% |
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
# Scrape yesterday's picks (default)
python cli_tool.py
```

### Output Files
| File | Description |
|------|-------------|
| `picks_YYYY-MM-DD.json` | Structured pick data |
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
    "units": 1.0
  }
]
```

---

## Benchmarks

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
│   ├── ocr_cascade.py       # Vision AI OCR engine
│   ├── ocr_handler.py       # OCR orchestration
│   ├── ocr_preprocessing.py # Image preprocessing
│   ├── ocr_validator.py     # OCR quality validation
│   ├── provider_pool.py     # Hybrid LLM provider pool
│   ├── prompt_builder.py    # AI prompt generation
│   ├── two_pass_verifier.py # Parsing verification
│   ├── cerebras_client.py   # Cerebras API client
│   ├── mistral_client.py    # Mistral API client
│   ├── openrouter_client.py # OpenRouter API client
│   ├── groq_client.py       # Groq API client
│   └── gemini_client.py     # Gemini API client
├── benchmark/
│   ├── ocr_benchmark.py     # Vision model benchmark
│   ├── parser_benchmark.py  # Parser model benchmark
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

### 6. Verify & Output
```python
from src.two_pass_verifier import TwoPassVerifier
TwoPassVerifier.verify_parsing_result(picks)
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `CEREBRAS_TOKEN not set` | Add token to `.env` file |
| `Groq 403 Access Denied` | Network/auth issue, use other providers |
| `Rate limited (429)` | Wait 1-2 minutes, reduce batch size |
| `Tesseract not found` | Install: `choco install tesseract` (Windows) |
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
| OCR Accuracy | 96%+ (Vision AI) |
| Parsing Accuracy | 100% |
| Avg OCR Time | 16.2s (Mistral) |
| Avg Parse Time | 0.9s (Cerebras) |
| Batch Throughput | 10 msgs/batch, 3 workers |

---

## Changelog

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

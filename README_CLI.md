# Telegram & Twitter Scraper CLI

This is a command-line interface version of the Sports Betting Scraper, designed for headless operation.

## Features
- **Telegram Scraping**: Fetches picks from configured channels.
- **Twitter Scraping**: Fetches tweets from target accounts using `tweepy`.
- **Deduplication**: Merges duplicate picks across platforms.
- **Smart OCR**: Automatically selects between Tesseract (local, fast) and Vision AI (cloud, accurate) based on image complexity.
- **Auto-Parsing**: Uses AI to extract structured pick data.
- **Validation**: Verifies picks and flags issues.

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**:
   - Ensure `.env` contains your keys:
     - `API_ID`, `API_HASH` (Telegram)
     - `TWITTER_BEARER_TOKEN` or `TWITTER_API_KEY`/`SECRET` (Twitter)
     - `OPENROUTER_API_KEY` (For AI Parsing)
   - Check `config.py` for target channels/accounts.

3. **Authentication (Telegram)**:
   - If this is your first time, you must run the **GUI App** (`python main.py`) first to log in to Telegram interactively. The session file is shared.

## Usage

Run the scraper:
```bash
python cli_tool.py
```

- **Date**: Defaults to "Yesterday" (Eastern Time) to capture the full previous day's picks.
- **Output**: 
  - Console summary.
  - `picks_YYYY-MM-DD.json` file in the current directory.
  - `cli_scraper.log` file.

## Note on Twitter
Twitter scraping requires valid API credentials. If `tweepy` fails to authenticate, Twitter scraping will be skipped, but Telegram scraping will continue.

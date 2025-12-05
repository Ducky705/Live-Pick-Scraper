import os

# ==============================================================================
# GITHUB ACTIONS: SNIPER SCHEDULE
# ==============================================================================
# Weekdays: 5:30 PM ET  -> 22:30 UTC
# Weekends: 11:30 AM ET -> 16:30 UTC
#           2:30 PM ET  -> 19:30 UTC
#           5:30 PM ET  -> 22:30 UTC
# ==============================================================================

YAML_CONTENT = """name: Sniper Pick Scraper

on:
  schedule:
    # WEEKDAYS (Mon-Fri): Run at 5:30 PM ET (22:30 UTC)
    - cron: '30 22 * * 1-5'
    
    # WEEKENDS (Sat-Sun): Run at 11:30 AM, 2:30 PM, 5:30 PM ET
    # UTC Equivalents: 16:30, 19:30, 22:30
    - cron: '30 16,19,22 * * 0,6'

  # Allows manual trigger for testing
  workflow_dispatch: 

jobs:
  run-sniper:
    runs-on: ubuntu-latest
    timeout-minutes: 8 # Hard limit to save money

    steps:
      - name: Check out code
        uses: actions/checkout@v4

      # --- CACHING STRATEGY ---
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip' 

      # Cache Tesseract to save ~30s setup time
      - name: Cache Tesseract
        id: cache-tesseract
        uses: actions/cache@v3
        with:
          path: /usr/bin/tesseract
          key: ${{ runner.os }}-tesseract-v1

      - name: Install System Dependencies
        if: steps.cache-tesseract.outputs.cache-hit != 'true'
        run: |
          sudo apt-get update
          sudo apt-get install -y tesseract-ocr libtesseract-dev

      - name: Install Python Dependencies
        run: |
          pip install -r requirements.txt

      - name: Run Pipeline
        env:
          TELEGRAM_API_ID: ${{ secrets.TELEGRAM_API_ID }}
          TELEGRAM_API_HASH: ${{ secrets.TELEGRAM_API_HASH }}
          TELEGRAM_SESSION_NAME: ${{ secrets.TELEGRAM_SESSION_NAME }}
          TELEGRAM_CHANNEL_URLS: ${{ secrets.TELEGRAM_CHANNEL_URLS }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}
          OPENROUTER_API_KEY: ${{ secrets.OPENROUTER_API_KEY }}
          AI_PARSER_MODEL: "google/gemini-2.0-flash-exp:free"
        run: |
          # The script will auto-exit early if no new data is found
          python main.py --force
"""

def write_yaml():
    # Ensure directory exists
    os.makedirs('.github/workflows', exist_ok=True)
    
    with open('.github/workflows/scrape_and_process.yml', 'w', encoding='utf-8') as f:
        f.write(YAML_CONTENT)
    print("✅ Sniper Schedule enforced in '.github/workflows/scrape_and_process.yml'")

if __name__ == "__main__":
    write_yaml()
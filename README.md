# Telegram Scraper 2.0 (CapperSuite) v2.0.0

CapperSuite is a standalone desktop application for aggregating and parsing sports betting picks from Telegram channels. It uses AI (LLM) and OCR to extract picks, odds, and units from structured and unstructured messages.

## Features

-   **Standalone Desktop App**: Native application for macOS and Windows. No Python installation required for end-users.
-   **AI-Powered Parsing**: Uses advanced LLMs (via OpenRouter) to extract picks from complex text.
-   **Integrated OCR**: Automatically extracts text from images (screenshots, slips) using Tesseract.
-   **Multi-Channel Sync**: Connects to your Telegram account and syncs selected channels.
-   **Smart Filtering**: Advanced table filtering and "Intelligence Refinery" for manual review.
-   **Auto-Review**: AI-powered review system to validate and correct pick metadata.
-   **CSV Export**: Export processed picks to CSV for analysis.
-   **Supabase Integration**: Optional integration for syncing picks to a central database.

## Installation

### For End Users
Download the latest release for your OS:
-   **macOS**: `TelegramScraper.app`
-   **Windows**: `TelegramScraper.exe`

Run the application. On first launch, you will be asked to log in with your Telegram phone number.

### For Developers

1.  Clone the repository:
    ```bash
    git clone https://github.com/Ducky705/Telegram-Scraper.git
    cd Telegram-Scraper
    ```

2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

3.  Configure `.env` (Create a `.env` file in root):
    ```env
    API_ID=your_api_id
    API_HASH=your_api_hash
    OPENROUTER_API_KEY=your_key
    SUPabase_URL=your_url
    SUPabase_KEY=your_key
    ```
    *Note: The standalone build packages the `.env` internally.*

4.  Run from source:
    ```bash
    python main.py
    ```

## Building from Source

See [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md) for detailed instructions on how to build the standalone executables for macOS and Windows using PyInstaller.

## Usage

1.  **Select Channels**: Choose the Telegram channels you want to scrape.
2.  **Fetch Messages**: Click "Initialize Data Fetch".
3.  **Refine**: Use the "Intelligence Refinery" to process messages with AI.
4.  **Export**: Export the final table to CSV or upload to the database.

## Architecture

-   **Frontend**: HTML/JS/CSS (Tailwind + Swiss Style) served via Flask.
-   **Backend**: Python (Flask + Waitress) running locally.
-   **GUI Wrapper**: `pywebview` creates a native window wrapper around the local web server.
-   **Data**: `user_session.session` stores Telegram auth state locally.

## License

Private / Proprietary
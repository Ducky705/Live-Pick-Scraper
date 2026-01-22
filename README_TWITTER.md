# Twitter Sports Scraper

This tool scrapes picks from Twitter accounts (specifically @EZMSports by default).

## key files
- `run_twitter_scraper.py`: The main script to fetch tweets and parse picks.
- `auth_twitter.py`: Helper script to log in and save session cookies.
- `src/twitter_client.py`: Core logic interacting with Twitter API (via Twikit).

## Setup
1. **Credentials**: Ensure your `.env` has Twitter credentials (used for fallback or initial check):
   ```
   TWITTER_USERNAME=...
   TWITTER_EMAIL=...
   TWITTER_PASSWORD=...
   ```
2. **Authentication**:
   Due to heavy bot protection (Cloudflare), you must log in once manually using the helper script:
   ```bash
   python auth_twitter.py
   ```
   - A window will pop up.
   - Log in to your account.
   - The window will close automatically when it detects a successful login.
   - This saves `twitter_cookies.json` which is used by the scraper.

## Usage
Run the scraper:
```bash
python run_twitter_scraper.py
```
It will:
1. Load cookies.
2. Fetch the latest 20 tweets.
3. Use the AI model to parse picks from the text.
4. Print the picks and save them to `twitter_picks.json`.

## Notes
- If the scraper starts failing with "403" or "Cloudflare" errors, simply run `python auth_twitter.py` again to refresh your cookies.
- To scrape a different user, edit the `target_username` variable in `run_twitter_scraper.py`.

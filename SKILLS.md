<tool_definitions>
These are the operational capabilities at your disposal within the CapperSuite architecture:

1. **Pick Orchestration (`src/live_pipeline.py`)**:
   - Capable of receiving `(message_text, image_paths)` and returning a classification (e.g. `PICK`) and a structured array of JSON picks.
   - Leverages a direct, non-SDK HTTP layer to interface with Gemini, Mistral, and OpenRouter in a strict fallback waterfall.
   - Automatically cleans LLM-provided markdown blocks to return raw parseable JSON.

2. **Capper & League Normalization (`src/supabase_client.py`)**
   - Implements fuzzy `get_or_create_capper_id(capper_name)` to sanitize and standardize capper identities before inserting them into Supabase.
   - Caches lists of Active Cappers (`_capper_map`, `_variant_map`), Leagues (`_league_map`), and Bet Types (`_bet_type_map`) in memory and hydrates them from Supabase via standard HTTP GET.

3. **Message Ingestion & Proxy Support (`live_runner.py`)** 
   - Downloads Telegram media locally to `TEMP_IMG_DIR` via Telethon for processing.
   - Orchestrates asynchronous tasks using `asyncio.gather` for concurrent Telegram, Discord, and Twitter consumption.
   - Safely cleans up image files from disk immediately after processing to prevent storage bloat.

4. **Benchmarking & Testing (`/benchmark/`, `/tests/`)**
   - Capable of generating "Golden Set" benchmark reports to systematically gauge the precision/accuracy of AI extractors against a ground-truth dataset over a wide variety of pick formats.
</tool_definitions>

<execution_commands>
Use these primary commands to execute the varying responsibilities of this repository. Always ensure `data/logs/` and `data/.sessions/` directories exist before running daemon processes.

- **Run the 24/7 Live Listener Daemon**:
  `python live_runner.py`
  *(Note: You can pass `--dry-run` to test ingestion and AI extraction without actually writing to Supabase, and `--no-catchup` to skip querying missed messages on boot).*

- **Run the CLI Interactive Tool (for manual setup and data backfilling)**:
  `python cli_tool.py`

- **Execute Test Suite**:
  `pytest tests/`

- **Run AI Extraction Benchmarks**:
  `python benchmark/benchmark_golden_set.py`

- **Linting & Formatting**:
  `ruff check .`
  `mypy .`
</execution_commands>

<data_protocols>
The system strict rules for communicating with external APIs and databases.

- **AI API Integrations**: 
  All LLM integrations (Gemini, Mistral, OpenRouter) utilize explicit, hand-rolled REST bindings (via `src/utils_urllib.py: post`) rather than large dependency-heavy official Python SDKs. 
  Images are base64-encoded manually before transiting to these vision models.

- **Supabase PostgreSQL Persistence**:
  Do NOT attempt to connect to Supabase utilizing `supabase-python`. 
  CapperSuite utilizes a deeply custom lightweight query builder wrapper in `src/supabase_client.py`.
  - Operations are performed using dictionary payloads wrapped into custom chains, e.g.:
    `client.table("live_structured_picks").insert(picks, ignore_duplicates=True).execute()`
  - HTTP `PATCH` and `POST` actions are handled internally using the `Prefer: return=representation,resolution=merge-duplicates` headers to simulate UPSERT.
  - Return formats are standardized duck-typed `type('obj', ...)` dict wrappers requiring checking `if getattr(res, 'error', None)`.

- **Social Scraping Integrations**:
  - *Telegram*: Handled native by `Telethon` (requires API Hash and ID).
  - *Twitter/X*: Polled via non-official APIs (e.g. `twikit`).
  - *Discord*: Managed via a standard `discord.py` Bot application.
</data_protocols>

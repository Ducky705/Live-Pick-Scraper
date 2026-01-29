# AGENTS.md - Developer Guide for AI Agents

This file provides instructions for AI agents (and human developers) working on the Sports Betting Telegram Scraper.
It serves as the ground truth for build, test, and style conventions.

## 1. Project Overview

- **Goal:** Scrape, parse, and grade sports betting picks from Telegram and Twitter channels.
- **Key Components:**
    - `cli_tool.py`: Main entry point for the CLI application.
    - `src/`: Core source code directory.
    - `benchmark/`: Benchmarking and grading tools (Crucial for optimization).
    - `tools/`: Utility scripts for maintenance and debugging.
    - `data/`: Runtime data storage (logs, output, cache, temp images).

## 2. Environment & Commands

### 2.1 Python Environment (CRITICAL)
- **Interpreter Path:**
  `/c/Users/diego/AppData/Local/Programs/Python/Python311/python.exe`
  
  **IMPORTANT:** Agents must ALWAYS use this absolute path for python commands to ensure the correct environment and dependencies are used. Do not rely on `python` or `python3` being in the PATH.

### 2.2 Core Commands

#### Installation
- **Install Dependencies:**
  ```bash
  /c/Users/diego/AppData/Local/Programs/Python/Python311/python.exe -m pip install -r requirements.txt
  ```

#### Execution
- **Run CLI:**
  ```bash
  /c/Users/diego/AppData/Local/Programs/Python/Python311/python.exe cli_tool.py
  ```

- **Run Benchmark (Platform Grader):**
  This is the primary way to verify changes to the extraction logic.
  ```bash
  /c/Users/diego/AppData/Local/Programs/Python/Python311/python.exe -m benchmark.run_platform_grader
  ```
  *Output:* `benchmark/reports/final_platform_grade.json`

#### Testing
- **Run All Tests (Pytest):**
  ```bash
  /c/Users/diego/AppData/Local/Programs/Python/Python311/python.exe -m pytest
  ```

- **Run Single Test File:**
  ```bash
  /c/Users/diego/AppData/Local/Programs/Python/Python311/python.exe -m pytest tests/path/to/test_file.py
  ```

#### Quality Assurance
- **Linting (Ruff):**
  ```bash
  ruff check .
  ```
- **Formatting (Ruff):**
  ```bash
  ruff format .
  ```

## 3. Code Style Guidelines

### 3.1 Python Standards
- **Version:** Python 3.10+ compatible code.
- **Type Hints:** STRICTLY REQUIRED for all function signatures. Use `typing` module (`List`, `Dict`, `Optional`, `Any`, `Tuple`).
  ```python
  def process_picks(picks: List[Dict[str, Any]]) -> Tuple[bool, str]:
      ...
  ```
- **Docstrings:** Google-style docstrings for complex functions and classes. Explain *why* and *args/returns*.
- **Naming:**
  - Variables/Functions: `snake_case` (e.g., `extract_picks`)
  - Classes: `PascalCase` (e.g., `ExtractionPipeline`)
  - Constants: `UPPER_CASE` (e.g., `MAX_RETRIES`)
  - Private Members: `_leading_underscore`

### 3.2 File Structure & Imports
- **Imports:** Use absolute imports starting from `src`.
  - *Good:* `from src.utils import backfill_odds`
  - *Bad:* `from ..utils import backfill_odds`
- **Path Handling:** Always use `os.path.join` or `pathlib.Path` for cross-platform compatibility (Windows/Linux).
- **Project Root:** Assume the working directory is the project root (`v0.0.15/`).

### 3.3 Error Handling & Logging
- **Logging:** Use the standard `logging` module. Do NOT use `print` for application logs.
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.error("Failed to fetch data: %s", error)
  ```
- **Exceptions:** Catch specific exceptions (`ValueError`, `requests.Timeout`). Avoid bare `except:` clauses.
- **Failures:** Fail gracefully. If a provider fails, fallback or return empty lists rather than crashing the whole pipeline.

## 4. Specific Workflows & Agents

### 4.1 Optimization Loops (Ralph)
When tasked with optimizing accuracy or speed, use the `ralph.exe` tool with the `benchmark_task.md` file.

- **Command:**
  ```bash
  ./ralph.exe --prompt-file benchmark_task.md --agent opencode --min-iterations 15 --max-iterations 50 --timeout 20 --completion-promise "OPTIMIZATION_COMPLETE" --raw
  ```
- **Strategy:**
  1. Run Benchmark.
  2. Analyze `final_platform_grade.json`.
  3. Implement fix/improvement.
  4. Re-run Benchmark.
  5. Commit if improved, Revert if regressed.

### 4.2 AI Provider Handling
- **Gemini:** Use `gemini-2.0-flash-exp` or `gemini-1.5-flash`.
- **Concurrency:** Respect rate limits.
  - Groq: Max ~2 concurrent (Free tier).
  - Gemini: Max ~2-3 concurrent.
- **Fallbacks:** Always implement fallbacks in `src/parallel_batch_processor.py`.

## 5. Critical Files Map
- **`src/extraction_pipeline.py`**: The brain of the operation. Orchestrates Regex -> AI -> Validation.
- **`src/parallel_batch_processor.py`**: Handles high-throughput AI requests with load balancing.
- **`src/rule_based_extractor.py`**: Fast-path extraction using Regex (Optimization target).
- **`benchmark/run_platform_grader.py`**: The judge. Runs the pipeline against the Goldenset.
- **`benchmark/dataset/goldenset_platform_500.json`**: The ground truth data.

## 6. Cursor/Copilot Rules
- **Conciseness:** Generate efficient, clean code. Avoid verbose comments unless explaining complex logic.
- **Safety:** Do not modify `config.py` or `.env` handling without explicit user instruction.
- **Testing:** Always verify changes with the Benchmark tool before marking a task complete.
- **Git:** Make granular commits. Message format: `type: description` (e.g., `fix: update gemini model name`, `feat: add parlay grouping`).

## 7. Troubleshooting
- **404 Errors (Gemini):** Usually means the model name is deprecated. Check `src/gemini_client.py`.
- **429 Errors (Rate Limit):** Reduce concurrency in `src/parallel_batch_processor.py`.
- **Import Errors:** Ensure `PYTHONPATH` includes the root directory or use the specific python executable provided above.

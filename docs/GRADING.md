# Grading System Documentation

The Grading System V3 is a modular, high-performance engine for evaluating betting picks against real-time game results. It replaces the monolithic legacy grader with a clean, extensible architecture.

## Overview

The grading pipeline follows this flow:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             GRADING ENGINE V3                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │ RAW PICK │──▶│   PICK   │───▶│  GRADER  │──▶│   GAME   │───▶│   ESPN   │   │
│  │   TEXT   │    │  PARSER  │    │  ENGINE  │    │  MATCHER │    │  SCORES  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                        │               │                        │
│                                        ▼               ▼                        │
│                                  ┌──────────┐    ┌──────────┐                   │
│                                  │ GRADING  │◀──│ MATCHED  │                   │
│                                  │  LOGIC   │    │   GAME   │                   │
│                                  └──────────┘    └──────────┘                   │
│                                        │                                        │
│                                        ▼                                        │
│                                  ┌──────────┐                                   │
│                                  │  GRADED  │                                   │
│                                  │  RESULT  │                                   │
│                                  └──────────┘                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Engine (`src/grading/engine.py`)
The central coordinator that orchestrates the grading process.
- **Input**: List of `Pick` objects and ESPN scores.
- **Process**: Routes picks to specific grading logic based on `BetType` (Spread, Total, Prop, etc.).
- **Output**: `GradedPick` objects with results (WIN/LOSS/PUSH/PENDING).

### 2. Parser (`src/grading/parser.py`)
Converts raw pick strings into structured data.
- **Features**:
  - Auto-detects bet types (Spread, Moneyline, Total, Props, Parlays).
  - Handles compact formats ("Lakers -5", "Over 210.5").
  - Recursively parses Parlays and Teasers.
  - Normalizes league names.

### 3. Matcher (`src/grading/matcher.py`)
Responsible for linking a text-based pick to a specific game entity.
- **Team Matching**: Uses `src/team_aliases.py` (500+ aliases) for robust fuzzy matching.
- **Player Matching**: Scans boxscores and leader lists for player props.
- **Optimization**: Pre-filters games by league to reduce search space.

### 4. Loader (`src/grading/loader.py`)
Abstraction layer for fetching data.
- Wraps `src/score_fetcher.py`.
- Handles on-demand boxscore fetching for detailed prop grading.

## Supported Bet Types

| Bet Type | Example | Grading Logic |
|----------|---------|---------------|
| **Spread** | `Lakers -5.5` | Winner if (Team Score + Spread) > Opponent Score |
| **Moneyline** | `Chiefs ML` | Winner if Team Score > Opponent Score |
| **Total** | `Over 220.5` | Winner if (Score 1 + Score 2) > Line |
| **Player Prop** | `LeBron: Pts O 25.5` | Checks boxscore stats vs line |
| **Parlay** | `Lakers -5 / Chiefs ML` | All legs must WIN (or PUSH); one LOSS kills it |
| **Period** | `1H Lakers -3` | Uses specific period linescores (1Q+2Q) |

## Usage

The primary entry point is `src/grader.py`, which provides a backward-compatible wrapper:

```python
from src.grader import grade_picks
from src.score_fetcher import fetch_scores_for_date

# 1. Fetch real-time scores
scores = fetch_scores_for_date("2026-01-22")

# 2. Grade picks
picks = [{"pick": "Lakers -5", "league": "NBA"}]
results = grade_picks(picks, scores)

# 3. Access results
print(results[0]["result"]) # "Win"
print(results[0]["score_summary"]) # "Lakers 110 (+5=115) vs Celtics 105"
```

## Performance & Optimization

The grading system includes several optimizations to ensure fast execution even with large batches of picks:

- **Persistent SQLite Cache**: Scores, boxscores, and odds are cached in `data/cache/espn_cache_v1.db`.
  - Scores: 24-hour TTL (immutable once final).
  - Boxscores: 7-day TTL (immutable once game ends).
  - Odds: 24-hour TTL.
- **Connection Pooling**: Uses a shared `requests.Session` with a connection pool to minimize TCP handshake overhead.
- **Parallel Fetching**: Scoreboards and odds for multiple leagues are fetched in parallel using a `ThreadPoolExecutor`.
- **League-Aware Fetching**: The scraper analyzes picks first and only requests scores for the leagues present in the batch, significantly reducing API calls.
- **Batch Boxscore Pre-fetching**: If player props are detected, the system pre-fetches all required boxscores in parallel before starting the grading loop, avoiding sequential network bottlenecks.
- **Live Game Filtering**: Only games with status `post` (final) are used for grading to ensure accuracy.

### Benchmarking

A benchmarking tool is available to measure performance:

```bash
python tools/benchmark_grader.py --iterations 2
```

Typical performance gains:
- **Cached Fetches**: ~100-250x faster than network calls.
- **Filtered Fetches**: ~10-15x faster than fetching all leagues.
- **End-to-End Grading**: ~6-8x faster than sequential processing.

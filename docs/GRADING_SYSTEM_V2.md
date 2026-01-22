# Grading System V2 Documentation

**Overview:**
The Grading System V2 is a robust, modular engine designed to automatically grade sports picks against real-time score data. It supports single bets, parlays, teasers, and props across multiple leagues.

## Features

- **Multi-Sport Support:** Seamlessly handles NFL, NBA, MLB, NHL, NCAAF, NCAAB, Tennis, Soccer, and more.
- **Parlay Logic:** Recursively grades multi-leg parlays, handling cross-league bets (e.g., NFL + NBA).
- **Team Aliases:** Intelligent normalization of team names (e.g., "Lakers", "LAL", "Los Angeles") using a centralized alias database.
- **Robust Score Fetching:** Integrates with `score_fetcher.py` to pull data from ESPN's undocumented API with parallel execution.
- **Batch Processing:** efficiently grades large batches of picks by pre-fetching all necessary score data.

---

## Architecture

The system is built around `src/grader_v2.py` as the core logic handler.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           GRADING SYSTEM V2                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐   │
│  │   INPUT  │───▶│  SCORE   │───▶│  FUZZY   │───▶│ GRADING  │───▶│  RESULT  │   │
│  │  PICKS   │    │ FETCHER  │    │ MATCHER  │    │  LOGIC   │    │  OBJECT  │   │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

1. **Input Normalization:** Picks are parsed into a standard dictionary format containing `selection`, `league`, and `date`.
2. **Data Retrieval:** `fetch_scores_for_date` pulls all games for the relevant dates.
3. **Matching Engine:** `find_game` fuzzy-matches pick text to game entities using `TEAM_ALIASES`.
4. **Grading Logic:**
    - **Moneyline:** Compares final scores.
    - **Spread:** Applies line to team score and compares.
    - **Totals:** Sums scores and compares to line.
    - **Parlays:** Splits legs by newline or `/` delimiter and grades recursively.
    - **Props:** (Experimental) Extracts player stats from boxscores.

---

## Supported Formats

The system adheres to the standards defined in `pick_format.md`.

### Single Bets
- **Moneyline:** `Lakers ML`
- **Spread:** `Chiefs -6.5`
- **Total:** `Lakers vs Celtics Over 215.5`

### Parlays
Format: `(League) Leg 1 / (League) Leg 2`

**Example:**
```text
(NFL) Dallas Cowboys -10.5 / (NBA) Lakers ML
```

### Props
Format: `Player Name: Stat Over/Under Value`

**Example:**
```text
LeBron James: Pts Over 25.5
```

---

## Usage

### Python API

```python
from src.grader_v2 import grade_batch

picks = [
    {"selection": "Lakers -5.5", "league": "NBA", "date": "2024-01-20"},
    {"selection": "(NFL) Chiefs ML / (NBA) Celtics -2", "league": "Other", "date": "2024-01-20"}
]

results = grade_batch(picks)

for res in results:
    print(f"Pick: {res['pick']} -> Grade: {res['grade']}")
```

### Grading Result Object

```json
{
    "pick": "(NFL) Chiefs ML / (NBA) Celtics -2",
    "grade": "WIN",
    "score_info": "", 
    "legs": [
        {"leg": "Chiefs ML", "grade": "WIN", "info": "Chiefs 27 - Bills 24"},
        {"leg": "Celtics -2", "grade": "WIN", "info": "Celtics 110 - Heat 105"}
    ],
    "details": "2 leg parlay"
}
```

---

## ESPN API Integration

The system uses `src/score_fetcher.py` to interface with ESPN.

- **Endpoints:** Uses `site.api.espn.com` for scoreboards and `sports.core.api.espn.com` for deep boxscores.
- **Parallelism:** Fetches multiple leagues concurrently for performance.
- **Aliases:** `src/team_aliases.py` maps hundreds of team variations to their official ESPN names.

## Future Improvements

- **Advanced Props:** Full implementation of `check_prop_condition` for all stat categories.
- **Teaser Support:** Dedicated logic to recognize "(Teaser)" prefixes and adjust lines dynamically.
- **Live Grading:** Websocket integration for real-time updates.

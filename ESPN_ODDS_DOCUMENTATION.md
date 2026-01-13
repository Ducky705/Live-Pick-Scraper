# ESPN Odds API - Complete Guide

## Overview
ESPN's odds API provides comprehensive betting odds for all major sports. The system fetches odds for all games on a given date and makes them available for lookup.

## API Endpoint
```
https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/events/{game_id}/competitions/{game_id}/odds
```

## Available Odds Types

### 1. Moneyline (Straight-up Winner)
**Description:** Bet on which team will win the game outright.

**Data Structure:**
```json
{
  "awayTeamOdds": {
    "current": {
      "moneyLine": {
        "value": 5.25,
        "displayValue": "21/4",
        "alternateDisplayValue": "+525",
        "decimal": 6.25,
        "fraction": "21/4",
        "american": "+525"
      }
    }
  },
  "homeTeamOdds": {
    "current": {
      "moneyLine": {
        "value": 1.17,
        "displayValue": "4/23",
        "alternateDisplayValue": "-575",
        "decimal": 1.17,
        "fraction": "4/23",
        "american": "-575"
      }
    }
  }
}
```

**Parsed Output:**
```python
{
    'moneyline': {
        'away': 425,   # American odds: +425 (underdog)
        'home': -575   # American odds: -575 (favorite)
    }
}
```

### 2. Point Spread
**Description:** Bet on the margin of victory. Team must win by more than the spread.

**Data Structure:**
```json
{
  "awayTeamOdds": {
    "spreadOdds": -115.0,    # Odds for taking the spread
    "current": {
      "pointSpread": {
        "alternateDisplayValue": "+13.5",  # Points given
        "american": "+13.5"
      }
    }
  },
  "homeTeamOdds": {
    "spreadOdds": -105.0,    # Odds for taking the spread
    "current": {
      "pointSpread": {
        "alternateDisplayValue": "-13.5",
        "american": "-13.5"
      }
    }
  },
  "spread": -13.5    # The spread line itself
}
```

**Parsed Output:**
```python
{
    'spread': {
        'away': -115,     # Odds for taking +13.5 spread
        'home': -105,     # Odds for taking -13.5 spread
        'line': -13.5       # Spread value
    }
}
```

### 3. Total (Over/Under)
**Description:** Bet on whether combined score will be over or under a set number.

**Data Structure:**
```json
{
  "overUnder": 249.5,     # Total line
  "overOdds": -110.0,       # Odds for taking the over
  "underOdds": -110.0       # Odds for taking the under
}
```

**Parsed Output:**
```python
{
    'total': {
        'line': 249.5,   # Total line
        'over': -110,      # Odds for taking over
        'under': -110       # Odds for taking under
    }
}
```

## Odds Formats Available

ESPN provides American odds in multiple formats:

| Format | Example | Description |
|--------|---------|-------------|
| American | -525, +525 | Standard US format (+/-) |
| Decimal | 6.25, 0.16 | European format (multiplier) |
| Fraction | 21/4, 1/6 | Traditional fractional odds |

## Odds Sources

Each bet type has multiple odds sources:

| Source | Description | Usage |
|--------|-------------|-------|
| `current` | Live/current odds | Best for live betting |
| `open` | Opening odds | Opening line when betting opened |
| `close` | Closing odds | Final line when betting closed |

## Supported Sports

| Sport | Sport Key | Leagues |
|--------|------------|---------|
| Basketball | basketball | nba, wnba, mens-college-basketball, womens-college-basketball |
| Football | football | nfl, college-football |
| Hockey | hockey | nhl |
| Baseball | baseball | mlb |
| Soccer | soccer | eng.1, usa.1, uefa.champions, etc. |
| MMA | mma | ufc |
| Golf | golf | pga, lpga |
| Racing | racing | f1, nascar-premier, indycar |
| Tennis | tennis | atp, wta |

## Usage Examples

### 1. Fetch Odds for a Date
```python
from src.score_fetcher import fetch_odds_for_date

# Fetch all odds for a specific date
odds_by_game = fetch_odds_for_date("2026-01-12")

# Returns dictionary: {game_id: {...}}
```

### 2. Look Up Odds for a Pick
```python
from src.score_fetcher import get_odds_for_pick

# Pre-fetched odds data
odds_data = fetch_odds_for_date("2026-01-12")

# Look up odds for various pick types
moneyline_odds = get_odds_for_pick("Utah Jazz", "NBA", "2026-01-12", odds_data)
spread_odds = get_odds_for_pick("Cleveland -13.5", "NBA", "2026-01-12", odds_data)
over_odds = get_odds_for_pick("Over 249.5", "NBA", "2026-01-12", odds_data)
under_odds = get_odds_for_pick("Under 250", "NBA", "2026-01-12", odds_data)

# Returns:
# moneyline_odds = 425   (Utah Jazz moneyline)
# spread_odds = -105    (Cleveland -13.5 spread odds)
# over_odds = -110      (Over 249.5 odds)
# under_odds = -110      (Under 250 odds)
```

### 3. Pick Type Detection

The system automatically detects bet type from pick text:

| Pick Text | Bet Type Detected | Odds Returned |
|-----------|-------------------|----------------|
| "Utah Jazz" | moneyline | moneyline odds |
| "Utah Jazz +13.5" | spread | spread odds |
| "Cleveland -13.5" | spread | spread odds |
| "Over 249.5" | over | over odds |
| "Under 250" | under | under odds |

## Integration Notes

1. **No Caching:** System processes 1 day at a time, no caching needed
2. **Best Odds Selection:** Always returns best available odds (highest American odds = best payout)
3. **No Backfilling:** Returns `None` if no match found, does not default to -110
4. **Team Name Matching:** Uses substring matching for flexible team name recognition
5. **Spread Detection:** Detects spread picks by looking for `+` or `-` with numbers

## Limitations

1. **No Prop Bets:** ESPN API does NOT provide:
   - Player props (e.g., "LeBron James Over 25.5 points")
   - Team props (e.g., "Lakers Over 210.5 team points")
   - Alternate lines (e.g., "Lakers +7.5")
   - Futures (e.g., "Lakers to win championship")
   - Live betting props
   - Period betting (e.g., "1st Half Over 105.5")

2. **Only Standard Bet Types:**
   - Moneyline (straight-up)
   - Point spread
   - Total (Over/Under)

3. **Historical Odds:** `open` and `close` sources provide opening and closing odds, but primary lookup uses `current` (live/available)

4. **No First Half / Second Half:** Does not provide odds for halftime bets
5. **No Quarter Betting:** Does not provide odds for NBA/NCAA quarters
6. **No Period Betting:** Does not provide odds for NFL quarters/innings

## Data Structure Reference

### Complete Parsed Odds Object
```python
{
    game_id: {
        'away_team': str,           # e.g., "Utah Jazz"
        'home_team': str,           # e.g., "Cleveland Cavaliers"
        'moneyline': {
            'away': int,            # e.g., 425
            'home': int              # e.g., -575
        },
        'spread': {
            'away': int,            # e.g., -115
            'home': int,            # e.g., -105
            'line': float           # e.g., -13.5
        },
        'total': {
            'line': float,           # e.g., 249.5
            'over': int,             # e.g., -110
            'under': int             # e.g., -110
        }
    }
}
```

## Example Data Flow

```
1. User scrapes Telegram picks for "2026-01-12"
2. System calls fetch_odds_for_date("2026-01-12")
3. System fetches all NBA/NFL/NBA games from ESPN
4. System queries odds API for each game ID
5. System parses all available odds types
6. For each pick, system looks up matching game
7. System returns appropriate odds based on bet type
8. Pick odds are available for display/use
```

## Error Handling

- Missing data: Returns `None`
- Invalid game ID: Skips silently
- API errors: Logged but continue processing
- No match found: Returns `None` for that pick

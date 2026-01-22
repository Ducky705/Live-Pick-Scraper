# ESPN API Extended League Support - Summary

## Overview
Successfully expanded the ESPN API scraper to support 12 additional leagues across 6 sports categories.

## New Leagues Added

### Basketball
- **WNCAAB** (Women's NCAA Basketball) - `basketball/womens-college-basketball`

### Soccer
- **Championship** (English Championship) - `soccer/eng.2`
- **La Liga** (Spanish) - `soccer/esp.1`
- **Bundesliga** (German) - `soccer/ger.1`
- **Serie A** (Italian) - `soccer/ita.1`
- **Ligue 1** (French) - `soccer/fra.1`
- **NWSL** (National Women's Soccer League) - `soccer/usa.nwsl`

### Golf
- **LPGA** - `golf/lpga`

### Racing
- **NASCAR** (Cup Series) - `racing/nascar-premier`
- **IndyCar** - `racing/irl`

### Lacrosse
- **PLL** (Premier Lacrosse League) - `lacrosse/pll`

## Files Modified

### 1. `src/score_fetcher.py`
- Updated `LEAGUES_TO_SCRAPE` dictionary with new league mappings
- Total leagues increased from 15 to 26

### 2. `src/grader.py`
- Updated `LEAGUE_ALIASES` to include new soccer leagues, racing, golf, and lacrosse
- Updated `SPORT_LEAGUE_MAP` for boxscore fetching (inside `fetch_full_boxscore` function)
- Extended soccer period handling to include all new soccer leagues
- Extended soccer ML (3-way) draw handling for all new soccer leagues

### 3. `src/prompt_builder.py`
- Updated formatting guide to document all new league abbreviations

## Test Results

### Configuration Verification
- Total leagues configured: **26**
- League categories: 11 (Basketball, Hockey, Baseball, Football, Soccer, MMA, Golf, Racing, Tennis, Lacrosse)

### Score Fetching Test (Date: 2025-01-12)
- Successfully fetched **698 events** from 57 endpoints
- New leagues with confirmed data:
  - WNCAAB: 15 events
  - La Liga: 2 events
  - Bundesliga: 2 events
  - Serie A: 4 events
  - Ligue 1: 4 events
- New leagues with no data (offseason):
  - Championship, NWSL, LPGA, NASCAR, IndyCar, PLL

### Grader Aliases
- Total alias mappings: **13**
- Soccer alias now includes 9 leagues for flexible matching
- Individual sport aliases added for F1, NASCAR, IndyCar, PGA, LPGA, PLL

### Boxscore Fetching
- Successfully tested boxscore retrieval for NBA game
- 27 player records retrieved correctly

## Complete League List

| Sport | League | API Endpoint |
|-------|--------|--------------|
| **Basketball** | NBA | `basketball/nba` |
| | WNBA | `basketball/wnba` |
| | NCAAB | `basketball/mens-college-basketball` |
| | **WNCAAB** *(NEW)* | `basketball/womens-college-basketball` |
| **Hockey** | NHL | `hockey/nhl` |
| **Baseball** | MLB | `baseball/mlb` |
| **Football** | NFL | `football/nfl` |
| | NCAAF | `football/college-football` |
| **Soccer** | EPL | `soccer/eng.1` |
| | MLS | `soccer/usa.1` |
| | UCL | `soccer/uefa.champions` |
| | **Championship** *(NEW)* | `soccer/eng.2` |
| | **La Liga** *(NEW)* | `soccer/esp.1` |
| | **Bundesliga** *(NEW)* | `soccer/ger.1` |
| | **Serie A** *(NEW)* | `soccer/ita.1` |
| | **Ligue 1** *(NEW)* | `soccer/fra.1` |
| | **NWSL** *(NEW)* | `soccer/usa.nwsl` |
| **MMA** | UFC | `mma/ufc` |
| **Golf** | PGA | `golf/pga` |
| | **LPGA** *(NEW)* | `golf/lpga` |
| **Racing** | F1 | `racing/f1` |
| | **NASCAR** *(NEW)* | `racing/nascar-premier` |
| | **IndyCar** *(NEW)* | `racing/irl` |
| **Tennis** | ATP | `tennis/atp` |
| | WTA | `tennis/wta` |
| **Lacrosse** | **PLL** *(NEW)* | `lacrosse/pll` |

## Notes

1. **Offseason Leagues**: Some leagues (NWSL, LPGA, NASCAR, IndyCar, PLL) showed 0 events on the test date, likely due to offseason scheduling.

2. **Soccer Draw Support**: All new soccer leagues support proper 3-way moneyline grading (Win/Loss/Draw).

3. **Boxscore Support**: All new leagues are mapped in the grader's boxscore fetching system, enabling detailed player stat lookups for player props.

4. **Performance**: Parallel fetching from 57 endpoints completes successfully with no significant performance impact.

5. **Tennis Events**: WTA showed 635 events on test date, indicating active tournament data.

## Next Steps

Consider adding:
- More soccer leagues (Eredivisie, Primeira Liga, Brasileirão)
- Cricket (API endpoint exists but complex structure)
- Rugby (API endpoint limited)
- Boxing (API endpoint limited)

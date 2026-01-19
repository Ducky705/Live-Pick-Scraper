# Sports Pick Data Specification

> **Version:** 3.0  
> **Last Updated:** 2026-01-18  
> **Status:** Canonical

---

## Table of Contents

1. [Overview](#1-overview)
2. [Data Model](#2-data-model)
3. [Field Reference](#3-field-reference)
4. [League Codes](#4-league-codes)
5. [Bet Types](#5-bet-types)
6. [Pick Value Format (Display String)](#6-pick-value-format-display-string)
7. [Structured Fields (Atomic Data)](#7-structured-fields-atomic-data)
8. [Sport-Specific Rules](#8-sport-specific-rules)
9. [Detection & Classification](#9-detection--classification)
10. [Validation & Rejection](#10-validation--rejection)
11. [Grading Integration](#11-grading-integration)
12. [AI Parser Contract](#12-ai-parser-contract)
13. [Golden Set Format](#13-golden-set-format)
14. [Examples](#14-examples)

---

## 1. Overview

This specification defines the canonical data format for sports betting picks across all systems: AI parsers, database storage, UI display, and grading engines.

### 1.1 Design Principles

| Principle | Description |
|-----------|-------------|
| **Dual Representation** | Every pick has BOTH a human-readable string (`pick`) AND structured atomic fields |
| **Separation of Concerns** | `pick` = what is bet, `odds` = price, `units` = stake size |
| **Queryability** | Structured fields enable database queries like "all LeBron props" |
| **Graceful Degradation** | Unknown values use explicit defaults, never null strings |
| **Source Attribution** | Every pick tracks its origin (capper, channel, deduction method) |

### 1.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         BetPick                             │
├─────────────────────────────────────────────────────────────┤
│  IDENTITY          │  CLASSIFICATION   │  DISPLAY           │
│  - message_id      │  - league         │  - pick (string)   │
│  - capper_name     │  - type           │                    │
│  - date            │  - tags           │                    │
├─────────────────────────────────────────────────────────────┤
│  STRUCTURED DATA   │  PRICING          │  METADATA          │
│  - subject         │  - odds           │  - ai_reasoning    │
│  - market          │  - units          │  - warning         │
│  - line            │                   │  - is_update       │
│  - prop_side       │                   │  - deduction_source│
├─────────────────────────────────────────────────────────────┤
│  GRADING                                                    │
│  - result                                                   │
│  - score_summary                                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Data Model

```python
class BetPick(BaseModel):
    # === IDENTITY ===
    message_id: Union[int, str]           # Source message identifier
    capper_name: str = "Unknown"          # Who made the pick
    date: Optional[str] = None            # "YYYY-MM-DD" format
    
    # === CLASSIFICATION ===
    league: str = "Other"                 # Sport/league code
    type: str = "Unknown"                 # Bet type
    tags: List[str] = []                  # ["Live", "Alt Line", "Max Bet"]
    
    # === DISPLAY STRING ===
    pick: str                             # Human-readable formatted pick
    
    # === STRUCTURED FIELDS (Atomic) ===
    subject: Optional[str] = None         # Team or player name
    market: Optional[str] = None          # Stat or market type
    line: Optional[float] = None          # Numerical line/total
    prop_side: Optional[str] = None       # "Over", "Under", "Yes", "No"
    
    # === PRICING ===
    odds: Optional[int] = None            # American odds (-110, +150)
    units: float = 1.0                    # Bet size
    
    # === METADATA ===
    ai_reasoning: Optional[str] = None    # "confidence | reason"
    warning: Optional[str] = None         # "Odds Mismatch", "Ambiguous"
    is_update: bool = False               # True if modifying previous pick
    deduction_source: str = "Explicit"    # "Explicit", "Implied", "Visual"
    
    # === GRADING ===
    result: str = "Pending"               # "Win", "Loss", "Push", "Pending"
    score_summary: Optional[str] = ""     # "LAL 112 - BOS 108"
```

---

## 3. Field Reference

### 3.1 Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `message_id` | int/str | Unique identifier from source (Telegram message ID) |
| `pick` | str | **Human-readable pick string.** See [Section 6](#6-pick-value-format-display-string) |
| `league` | str | Sport/league code. Default: `"Other"` |
| `type` | str | Bet type. Default: `"Unknown"` |

### 3.2 Attribution Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `capper_name` | str | `"Unknown"` | Name of the handicapper/tipster |
| `date` | str | `null` | Pick date in `YYYY-MM-DD` format |
| `deduction_source` | str | `"Explicit"` | How the pick was identified |

**Deduction Source Values:**

| Value | Meaning |
|-------|---------|
| `Explicit` | Clearly stated in text |
| `Implied` | Inferred from context |
| `Visual` | Extracted from image/ticket |

### 3.3 Structured Fields (Atomic Data)

These fields decompose `pick` into queryable components:

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `subject` | str | The entity being bet on | `"LeBron James"`, `"Kansas City Chiefs"` |
| `market` | str | The stat or market | `"Pts"`, `"Spread"`, `"ML"`, `"Total"` |
| `line` | float | The numerical line | `25.5`, `-7`, `220.5` |
| `prop_side` | str | Direction for O/U props | `"Over"`, `"Under"`, `null` |

### 3.4 Pricing Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `odds` | int | `null` | American odds. Store as integer: `-110`, `150` (not `+150`) |
| `units` | float | `1.0` | Bet size. `"2u"` → `2.0` |

### 3.5 Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `tags` | list | Labels: `["Live", "Alt Line", "Hedge", "Max Bet"]` |
| `warning` | str | Anomalies: `"Odds Mismatch"`, `"Ambiguous Entity"` |
| `is_update` | bool | `true` if this modifies a previous pick |
| `ai_reasoning` | str | Format: `"85 \| Clear spread bet from ticket"` |

### 3.6 Grading Fields

| Field | Type | Values |
|-------|------|--------|
| `result` | str | `"Pending"`, `"Win"`, `"Loss"`, `"Push"`, `"Cancelled"` |
| `score_summary` | str | Final score: `"LAL 112 - BOS 108"` |

---

## 4. League Codes

| Code | Sport | Description |
|------|-------|-------------|
| `NFL` | Football | National Football League |
| `NCAAF` | Football | NCAA FBS |
| `CFL` | Football | Canadian Football League |
| `NBA` | Basketball | National Basketball Association |
| `NCAAB` | Basketball | NCAA Division I |
| `WNBA` | Basketball | Women's NBA |
| `MLB` | Baseball | Major League Baseball |
| `NHL` | Hockey | National Hockey League |
| `EPL` | Soccer | English Premier League |
| `LALIGA` | Soccer | Spanish La Liga |
| `SERIEA` | Soccer | Italian Serie A |
| `BUNDESLIGA` | Soccer | German Bundesliga |
| `LIGUE1` | Soccer | French Ligue 1 |
| `UCL` | Soccer | UEFA Champions League |
| `MLS` | Soccer | Major League Soccer |
| `UFC` | MMA | Ultimate Fighting Championship |
| `PFL` | MMA | Professional Fighters League |
| `BELLATOR` | MMA | Bellator MMA |
| `BOXING` | Combat | Professional Boxing |
| `TENNIS` | Tennis | ATP / WTA / Grand Slams |
| `PGA` | Golf | PGA Tour |
| `LIV` | Golf | LIV Golf |
| `F1` | Motorsport | Formula 1 |
| `NASCAR` | Motorsport | NASCAR |
| `Other` | Any | Multi-sport parlays OR unknown |

### League Rules

- **Single-sport parlay:** Use that sport's code
- **Multi-sport parlay:** Use `Other`
- **Unknown:** Use `Other`
- **Never concatenate:** `"NFL/NBA"` is invalid

---

## 5. Bet Types

| Type | Description | Has Line? | Has Side? |
|------|-------------|-----------|-----------|
| `Moneyline` | Win outright | No | No |
| `Spread` | Point spread / handicap | Yes | No |
| `Total` | Combined score O/U | Yes | Yes |
| `Player Prop` | Player stat O/U | Yes | Yes |
| `Team Prop` | Team stat O/U | Yes | Yes |
| `Game Prop` | Game event | Maybe | Maybe |
| `Period` | Partial game bet | Yes | Maybe |
| `Parlay` | Multi-leg bet | N/A | N/A |
| `Teaser` | Adjusted spread parlay | N/A | N/A |
| `Future` | Long-term outcome | No | No |
| `Unknown` | Cannot classify | N/A | N/A |

---

## 6. Pick Value Format (Display String)

The `pick` field is a **human-readable string** for UI display.

### 6.1 Global Rules

1. **No odds:** `Lakers -5.5 (-110)` → pick: `Lakers -5.5`, odds: `-110`
2. **No units:** `2u Lakers ML` → pick: `Lakers ML`, units: `2.0`
3. **No trailing decimals:** `25` not `25.0` (keep `25.5`)
4. **Consistent separators:** `:` for props, `vs` for matchups, `/` for parlays

### 6.2 Format by Type

#### Moneyline
```
{Team/Player} ML

Examples:
  Los Angeles Lakers ML
  Patrick Mahomes MVP ML
```

#### Spread
```
{Team} {+/-Line}

Examples:
  Kansas City Chiefs -7.5
  New York Giants +3
  Arsenal -1
```

#### Total
```
{Away} vs {Home} {Over/Under} {Number}

Examples:
  Lakers vs Celtics Over 220.5
  Chiefs vs Eagles Under 48
```

#### Player Prop
```
{Player Name}: {Stat} {Over/Under} {Number}

Examples:
  LeBron James: Pts Over 25.5
  Patrick Mahomes: PassYds Over 275.5
  Travis Kelce: Rec Over 5.5
```

#### Team Prop
```
{Team}: {Stat} {Over/Under} {Number}

Examples:
  Dallas Cowboys: Total Points Over 24.5
  Lakers: 3PM Over 12.5
```

#### Game Prop
```
{Description}: {Selection}

Examples:
  First TD Scorer: Travis Kelce
  Fight to go the Distance: No
```

#### Period
```
{Period} {Standard Format}

Examples:
  1H Chiefs -3.5
  1H Lakers vs Celtics Over 110.5
  1Q Thunder -2
  F5 Yankees -0.5
  P1 Rangers ML
```

#### Parlay
```
{Leg 1} / {Leg 2} / ...

Examples:
  Chiefs -7 / Lakers ML
  Duke -3 / Kansas ML
```

#### Teaser
```
Teaser {Pts}pt: {Leg 1} / {Leg 2} / ...

Examples:
  Teaser 6pt: Chiefs -1.5 / Eagles +9
```

#### Future
```
{Event}: {Selection}

Examples:
  Super Bowl Winner: Kansas City Chiefs
  NBA MVP: Luka Doncic
```

---

## 7. Structured Fields (Atomic Data)

For **every non-parlay pick**, populate structured fields:

### 7.1 Mapping by Type

| Type | subject | market | line | prop_side |
|------|---------|--------|------|-----------|
| Moneyline | Team/Player | `"ML"` | `null` | `null` |
| Spread | Team | `"Spread"` | `-7.5` | `null` |
| Total | `"{Away} vs {Home}"` | `"Total"` | `220.5` | `"Over"` |
| Player Prop | Player name | `"Pts"`, `"Yds"` | `25.5` | `"Over"` |
| Team Prop | Team name | `"Points"` | `24.5` | `"Over"` |
| Period | Team or matchup | `"Spread"`, `"Total"` | value | side if O/U |
| Future | Selection | Event name | `null` | `null` |

### 7.2 Examples

```json
// Spread
{
  "pick": "Kansas City Chiefs -7.5",
  "type": "Spread",
  "subject": "Kansas City Chiefs",
  "market": "Spread",
  "line": -7.5,
  "prop_side": null
}

// Player Prop
{
  "pick": "LeBron James: Pts Over 25.5",
  "type": "Player Prop",
  "subject": "LeBron James",
  "market": "Pts",
  "line": 25.5,
  "prop_side": "Over"
}

// Total
{
  "pick": "Lakers vs Celtics Over 220.5",
  "type": "Total",
  "subject": "Lakers vs Celtics",
  "market": "Total",
  "line": 220.5,
  "prop_side": "Over"
}

// Moneyline
{
  "pick": "Los Angeles Lakers ML",
  "type": "Moneyline",
  "subject": "Los Angeles Lakers",
  "market": "ML",
  "line": null,
  "prop_side": null
}
```

### 7.3 Parlay Structured Data

For parlays, structured fields are `null`. The legs are encoded in the `pick` string.

Future enhancement: `legs: []` array field for parsed parlay legs.

---

## 8. Sport-Specific Rules

### 8.1 Tennis

| Bet | pick format | market |
|-----|-------------|--------|
| Match Winner | `Djokovic ML` | `ML` |
| Set Spread | `Nadal -1.5 sets` | `Sets` |
| Game Spread | `Alcaraz +4.5 games` | `Games` |
| Total Games | `Djokovic vs Alcaraz Over 38.5 games` | `Total Games` |
| Set Winner | `Sinner to win Set 1` | `Set 1 Winner` |

### 8.2 Soccer

| Bet | pick format | Notes |
|-----|-------------|-------|
| Match Winner | `Arsenal ML` | 90 minutes (includes injury time) |
| Draw | `Arsenal vs Chelsea Draw` | type: `Moneyline` |
| Regulation | `60 min Arsenal ML` | Excludes extra time |
| Asian Handicap | `Liverpool -1.5` | type: `Spread` |
| Goals O/U | `Arsenal vs Chelsea Over 2.5` | type: `Total` |
| BTTS | `Arsenal vs Chelsea BTTS: Yes` | type: `Game Prop` |

### 8.3 Hockey

- **Puck Line:** `{Team} ±1.5`
- **Regulation:** `60 min {Team} ML` (no OT)
- **Periods:** `P1`, `P2`, `P3`

### 8.4 Baseball

- **Run Line:** `{Team} ±1.5`
- **First 5:** `F5 {Team} {line}` or `F5 {Away} vs {Home} O/U {total}`

---

## 9. Detection & Classification

### 9.1 Period Triggers

If raw text matches ANY pattern, `type` = `Period`:

| Pattern | Identifier |
|---------|------------|
| `1st half`, `first half`, `1H` | `1H` |
| `2nd half`, `second half`, `2H` | `2H` |
| `1st quarter`, `1Q` | `1Q` |
| `1st period`, `P1` | `P1` |
| `first 5`, `F5` | `F5` |
| `60 min`, `regulation` | `60 min` |

### 9.2 Parlay Indicators

- Multiple teams with `/`, `+`, or line breaks
- Words: `parlay`, `combo`, `accumulator`
- Multiple odds for single bet

### 9.3 Prop Detection

| Signal | Classification |
|--------|----------------|
| Player name + stat word | `Player Prop` |
| Team name + `total points`, `team total` | `Team Prop` |
| `first to score`, `anytime scorer` | `Game Prop` |

### 9.4 Spread vs Moneyline

- Has `+/-` number → `Spread`
- Has `ML` or no number → `Moneyline`
- `PK` / `Pick'em` → `Spread` with `line: 0`

---

## 10. Validation & Rejection

### 10.1 Required for Valid Pick

- [ ] `pick` is non-empty
- [ ] `league` is valid code
- [ ] `type` is valid type

### 10.2 Reject These

| Pattern | Reason |
|---------|--------|
| `"DM for picks"`, `"Join VIP"` | Marketing |
| `"5-2 this week"`, `"on a heater"` | Record statement |
| `"Bet 2% bankroll"` | Advice, not pick |
| `"LOCK OF THE DAY"` (no team) | Header only |
| `"Hard Rock"`, `"DraftKings"` | Sportsbook name |

### 10.3 Warnings (Valid but Flagged)

| Condition | Warning Value |
|-----------|---------------|
| Player name is ambiguous (`"Jones"`) | `"Ambiguous Entity"` |
| OCR odds ≠ ticket odds | `"Odds Mismatch"` |
| Unusual line (e.g., -25.5) | `"Unusual Line"` |

---

## 11. Grading Integration

### 11.1 Result Values

| Value | Meaning |
|-------|---------|
| `Pending` | Not yet graded |
| `Win` | Pick covered |
| `Loss` | Pick did not cover |
| `Push` | Exact line hit, bet returned |
| `Cancelled` | Game cancelled/voided |

### 11.2 Score Summary Format

```
{Away Team} {Away Score} - {Home Team} {Home Score}

Example: LAL 112 - BOS 108
```

### 11.3 Grading Requirements

To grade a pick, the system needs:
- `subject` (to match team/player)
- `market` (to know what to check)
- `line` (to compare against)
- `prop_side` (for O/U comparison)

This is why structured fields are critical.

---

## 12. AI Parser Contract

The AI parser must output this structure:

```json
{
  "picks": [
    {
      "id": 12345,
      "cn": "CapperName",
      "lg": "NBA",
      "ty": "Spread",
      "p": "Lakers -5.5",
      "od": -110,
      "u": 1.0,
      "sub": "Los Angeles Lakers",
      "mkt": "Spread",
      "ln": -5.5,
      "side": null,
      "tags": [],
      "src": "Explicit"
    }
  ]
}
```

**Key Mapping:**

| Short | Full Field |
|-------|------------|
| `id` | `message_id` |
| `cn` | `capper_name` |
| `lg` | `league` |
| `ty` | `type` |
| `p` | `pick` |
| `od` | `odds` |
| `u` | `units` |
| `sub` | `subject` |
| `mkt` | `market` |
| `ln` | `line` |
| `side` | `prop_side` |
| `src` | `deduction_source` |

---

## 13. Golden Set Format

For training/validation, use JSONL format:

```jsonl
{"image_path": "img/001.jpg", "ocr_text": "Lakers -5.5 (-110)", "expected_picks": [{"league": "NBA", "type": "Spread", "pick": "Los Angeles Lakers -5.5", "odds": -110, "subject": "Los Angeles Lakers", "market": "Spread", "line": -5.5, "prop_side": null}]}
```

Each line contains:
- `image_path`: Source image
- `ocr_text`: Raw text from image
- `expected_picks`: Array of correctly formatted picks

---

## 14. Examples

### 14.1 Complete Examples

```json
// NBA Spread
{
  "message_id": 12345,
  "capper_name": "SharpAction",
  "league": "NBA",
  "type": "Spread",
  "pick": "Los Angeles Lakers -5.5",
  "odds": -110,
  "units": 2.0,
  "subject": "Los Angeles Lakers",
  "market": "Spread",
  "line": -5.5,
  "prop_side": null,
  "tags": [],
  "deduction_source": "Explicit",
  "result": "Pending"
}

// NFL Player Prop
{
  "message_id": 12346,
  "capper_name": "PropKing",
  "league": "NFL",
  "type": "Player Prop",
  "pick": "Patrick Mahomes: PassYds Over 275.5",
  "odds": -115,
  "units": 1.0,
  "subject": "Patrick Mahomes",
  "market": "PassYds",
  "line": 275.5,
  "prop_side": "Over",
  "tags": [],
  "deduction_source": "Visual",
  "result": "Win",
  "score_summary": "Mahomes: 312 yards"
}

// Multi-Sport Parlay
{
  "message_id": 12347,
  "capper_name": "ParlayPete",
  "league": "Other",
  "type": "Parlay",
  "pick": "Chiefs -7 / Lakers ML / Duke -3",
  "odds": 595,
  "units": 1.0,
  "subject": null,
  "market": null,
  "line": null,
  "prop_side": null,
  "tags": [],
  "deduction_source": "Explicit",
  "result": "Loss"
}
```

### 14.2 Raw → Formatted

| Raw Input | Formatted Output |
|-----------|------------------|
| `Chiefs -7 (-110)` | pick: `Kansas City Chiefs -7`, odds: `-110`, type: `Spread` |
| `LAL ML +150 2u` | pick: `Los Angeles Lakers ML`, odds: `150`, units: `2`, type: `Moneyline` |
| `Mahomes o275 pass` | pick: `Patrick Mahomes: PassYds Over 275`, type: `Player Prop`, market: `PassYds`, line: `275`, side: `Over` |
| `1H over 110` | pick: `1H Unknown vs Unknown Over 110`, type: `Period` |
| `parlay: Chiefs + Lakers` | pick: `Chiefs ML / Lakers ML`, type: `Parlay`, league: `Other` |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 3.0 | 2026-01-18 | Added structured fields, AI contract, golden set format, grading integration |
| 2.0 | 2026-01-18 | Added detection rules, validation, sport-specific rules |
| 1.0 | 2025-xx-xx | Initial format specification |

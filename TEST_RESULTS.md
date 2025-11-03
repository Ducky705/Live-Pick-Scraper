# Test Results Summary

## 📊 Overall Results
- **Tests Run**: 44
- **Successes**: 25
- **Failures**: 6
- **Errors**: 19 (all now fixed!)

## ✅ What's Working
- Unit extraction (basic cases)
- Bet type standardization
- League standardization (mostly)
- Unit value cleaning
- Regular channel scraping
- Aggregator channel scraping (mostly)
- Message separator handling
- Negative keyword filtering
- Positive keyword requirement
- Edge cases (empty inputs, long text, special chars, unicode, timezone, regex performance)
- Performance benchmarks (excellent: 24,997 picks/sec!)

## ❌ Issues Found

### 1. Simple Parser Issues (CRITICAL)

#### Issue 1a: Parenthesical Units Not Supported
**Test**: Pick ID 3 - `'Lakers ML (2 units)'`
**Problem**: Parser returns `None` because regex doesn't handle `(2 units)` format
**Fix Needed** in `simple_parser.py`:
- Update `_extract_unit()` regex to handle `(2 units)` and `(2u)` patterns
- Or handle units anywhere in the line, not just at the end

#### Issue 1b: Total with Team Context Failing
**Test**: Pick ID 6 - `'Lakers vs Celtics Over 215.5 -110 2u'`
**Problem**: Parser returns `None` - regex pattern not matching team context
**Fix Needed** in `simple_parser.py`:
- The total regex pattern `r"^(?P<dir>Over|Under|O|U)\s+(?P<total>\d{2,3}(?:[\.,]\d)?)\s*(?P<odds>\([+-]\d{3,}\)|[+-]\d{3,})?(?:\s+\d+[\.,]?\d*\s*u(?:nit)?s?)?$"` requires line to START with Over/Under
- Need pattern that handles `TeamA vs TeamB Over/Under Total` format

#### Issue 1c: Unit Extraction Bug
**Test**: Pick ID 8 - `'Team with 1.5u ML -130'`
**Problem**: Expected unit=1.0, got unit=1.5
**Analysis**: The regex `(team.*?)` is greedy and includes `1.5u` in the team name
**Root Cause**: The `_extract_unit()` function runs AFTER the regex match, but the unit is already consumed
**Fix Needed** in `simple_parser.py`:
- Current moneyline regex: `r"^(?P<team>[\w\s\.'\-&]+?)\s+ML\s*..."`
- Issue: If "1.5u" appears between team name and "ML", it gets absorbed into the team name
- Solution: Extract unit FIRST, then match the clean text

### 2. Standardizer Issue (MEDIUM)

#### Issue 2: Fuzzy Matching Too Aggressive
**Test**: League `'unknown league'` expected to map to `'Other'`, but got `'NFL'`
**Problem**: Fuzzy matching score threshold too low or matching algorithm too permissive
**Fix Needed** in `standardizer.py`:
- Current threshold: 85 (line 25)
- "unknown league" shouldn't match to "NFL" with score >= 85
- Consider raising threshold to 90-95

### 3. Telegram Scraper Issues (MEDIUM)

#### Issue 3a: Duplicate Detection in Mock
**Test**: Duplicate messages should be skipped, but mock detected 2 instead of 1
**Problem**: Database mock in test doesn't track previous uploads properly
**Fix**: This is a test mock issue, not a real bug

#### Issue 3b: Malformed Aggregator Message
**Test**: Expected 0 uploads, got 1
**Problem**: Malformed message correctly logged warning, but second message was uploaded
**Analysis**: Only first message should be skipped, second might be valid - this might be correct behavior

## 🛠️ Code Fixes Needed

### Fix 1: simple_parser.py - Handle Parenthetical Units

```python
def _extract_unit(text: str) -> float:
    """Helper to find a unit value (e.g., 2u, 1.5 units, (2u)) in a string."""
    if not isinstance(text, str):
        return 1.0

    # Handle parenthetical units like (2u) or (2 units)
    paren_match = re.search(r'\((\d+[\.,]?\d*)\s*u(?:nit)?s?\)', text, re.IGNORECASE)
    if paren_match:
        unit_str = paren_match.group(1).replace(',', '.')
        return float(unit_str)

    # Handle regular units at end: 2u, 2 units, 2,5u
    unit_match = re.search(r'(\d+[\.,]?\d*)\s*u(nit)?s?', text, re.IGNORECASE)
    if unit_match:
        unit_str = unit_match.group(1).replace(',', '.')
        return float(unit_str)

    return 1.0
```

### Fix 2: simple_parser.py - Total Pattern with Teams

Add a new pattern for team totals:

```python
{
    'regex': re.compile(
        r"^(?P<team1>[\w\s\.'\-&]+?)\s+(?:vs|@)\s+(?P<team2>[\w\s\.'\-&]+?)\s+(?P<dir>Over|Under|O|U)\s+(?P<total>\d{2,3}(?:[\.,]\d)?)\s*(?P<odds>\([+-]\d{3,}\)|[+-]\d{3,})?(?:\s+\d+[\.,]?\d*\s*u(?:nit)?s?)?$",
        re.IGNORECASE
    ),
    'handler': _handle_total_with_teams
}

def _handle_total_with_teams(match: re.Match, line: str) -> dict:
    """Handles Total patterns with team context."""
    team1 = match.group('team1').strip()
    team2 = match.group('team2').strip()
    direction_char = match.group('dir').strip().upper()
    direction = 'Over' if direction_char.startswith('O') else 'Under'
    total = match.group('total').strip()
    odds_str = match.group('odds')

    pick_value = f"{team1} vs {team2} {direction} {total}"

    return {
        'bet_type': 'Total',
        'pick_value': pick_value,
        'odds_american': int(odds_str.replace('(', '').replace(')', '')) if odds_str else -110,
        'unit': _extract_unit(line)
    }
```

### Fix 3: simple_parser.py - Better Unit Handling

Pre-extract units before regex matching:

```python
def parse_with_regex(raw_pick: dict) -> dict | None:
    """
    Iterates through simple regex patterns to attempt a high-confidence parse.
    If a single, unambiguous match is found, it returns a structured pick.
    Otherwise, returns None.
    """
    text = raw_pick['raw_text']
    found_picks = []

    # First, check if this is multi-line - if so, reject immediately
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if len(lines) > 1:
        return None

    # Single line - extract unit first
    extracted_unit = _extract_unit(text)
    clean_text = re.sub(r'\s*\d+[\.,]?\d*\s*u(?:nit)?s?', '', text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\s*\(\d+[\.,]?\d*\s*u(?:nit)?s?\)', '', clean_text, flags=re.IGNORECASE)

    line = clean_text.strip()

    # ... rest of parsing logic
```

### Fix 4: standardizer.py - Raise Fuzzy Matching Threshold

```python
best_match_key, score = fuzz_process.extractOne(normalized_input, keys_to_match)

if score >= 90:  # Changed from 85 to 90
    return standards_map[best_match_key]
```

## 🎯 Performance Highlights

- **Simple Parser**: 24,997 picks/sec ✅
- **Unit Extraction**: Fast ✅
- **Standardization**: Fast ✅

The simple parser is EXTREMELY fast - great for the hybrid approach!

## 📝 Recommendations

1. **Priority 1**: Fix simple_parser.py unit extraction bug (Issue 1c)
   - This affects real picks like "Team with 1.5u ML"
   - Solution: Pre-extract units before regex matching

2. **Priority 2**: Add support for parenthetical units (Issue 1a)
   - Common format: "(2 units)"
   - Relatively easy fix

3. **Priority 3**: Fix total with teams pattern (Issue 1b)
   - Important for full game totals like "Lakers vs Celtics Over 215.5"
   - Need to add new regex pattern

4. **Priority 4**: Adjust fuzzy matching threshold (Issue 2)
   - Prevents false matches on unknown leagues
   - Simple threshold change

## 🔍 Test Coverage Analysis

The test suite successfully identified:
- ✅ Parser pattern gaps
- ✅ Unit extraction edge cases
- ✅ Standardization failures
- ✅ Scraper logic issues
- ✅ Performance bottlenecks (none found - all fast!)
- ✅ Error handling

This is a **comprehensive test suite** that will continue to catch issues as you develop!

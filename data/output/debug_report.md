# Production Run Debug Report (2026-01-24)

## Run Stats
- **Total Run Time**: ~5 minutes 35 seconds (14:10:17 to 14:15:52)
- **Total Picks Extracted**: 61
- **Picks with Odds**: 39
- **Picks with Results**: 54 (Wins: 20, Losses: 33, Pushes: 1)
- **Pending/Unknown**: 7

## Errors & Parser Issues
No critical structural parsing errors found.

## OCR vs Parser Results
Below is the raw text + OCR and the structured parsed output for every pick.

### Pick 1: Porterpicks - Tennessee vs Alabama Over 167.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31633",
  "capper_name": "Porterpicks",
  "league": "NCAAB",
  "type": "Total",
  "pick": "Tennessee vs Alabama Over 167.5",
  "line": 167.5,
  "odds": -110,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit total with team names",
  "id": "31633",
  "cn": "Porterpicks",
  "lg": "NCAAB",
  "ty": "Total",
  "p": "Tennessee vs Alabama Over 167.5",
  "od": null,
  "u": 3.0,
  "prop_side": "Over",
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Loss",
  "score_summary": "Total: 152.0 vs 167.5",
  "game_id": "401808199"
}
```

### Pick 2: Porterpicks - Krylov ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31629",
  "capper_name": "Porterpicks",
  "league": "UFC",
  "type": "Moneyline",
  "pick": "Krylov ML",
  "line": null,
  "odds": 120,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML with odds",
  "id": "31629",
  "cn": "Porterpicks",
  "lg": "UFC",
  "ty": "Moneyline",
  "p": "Krylov ML",
  "od": 120,
  "u": 2.0,
  "result": "Pending",
  "score_summary": "Game not found"
}
```

### Pick 3: Porterpicks - Figueiredo vs Nurmagomedov Under 2.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31629",
  "capper_name": "Porterpicks",
  "league": "UFC",
  "type": "Total",
  "pick": "Figueiredo vs Nurmagomedov Under 2.5",
  "line": 2.5,
  "odds": 130,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit total with team names and odds",
  "id": "31629",
  "cn": "Porterpicks",
  "lg": "UFC",
  "ty": "Total",
  "p": "Figueiredo vs Nurmagomedov Under 2.5",
  "od": 130,
  "u": 1.0,
  "prop_side": "Under",
  "result": "Pending",
  "score_summary": "Game not found"
}
```

### Pick 4: Porterpicks - Pimblett vs Gaethje Over 2.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31629",
  "capper_name": "Porterpicks",
  "league": "UFC",
  "type": "Total",
  "pick": "Pimblett vs Gaethje Over 2.5",
  "line": 2.5,
  "odds": -120,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit total with team names and odds",
  "id": "31629",
  "cn": "Porterpicks",
  "lg": "UFC",
  "ty": "Total",
  "p": "Pimblett vs Gaethje Over 2.5",
  "od": -120,
  "u": 3.0,
  "prop_side": "Over",
  "result": "Pending",
  "score_summary": "Game not found"
}
```

### Pick 5: HammeringHank - California +4.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31632",
  "capper_name": "HammeringHank",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "California +4.5",
  "line": 4.5,
  "odds": null,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31632",
  "cn": "HammeringHank",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "California +4.5",
  "od": null,
  "u": 3.0,
  "result": "Win",
  "score_summary": "California Golden Bears 78.0 (+4.5=82.5) vs Stanford Cardinal 66.0",
  "game_id": "401820695"
}
```

### Pick 6: HammeringHank - Nevada +8.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31632",
  "capper_name": "HammeringHank",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Nevada +8.5",
  "line": 8.5,
  "odds": null,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31632",
  "cn": "HammeringHank",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Nevada +8.5",
  "od": null,
  "u": 2.0,
  "result": "Pending",
  "score_summary": "Game not found"
}
```

### Pick 7: HammeringHank - Cincinnati -2.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31632",
  "capper_name": "HammeringHank",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Cincinnati -2.5",
  "line": -2.5,
  "odds": null,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31632",
  "cn": "HammeringHank",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Cincinnati -2.5",
  "od": null,
  "u": 2.0,
  "result": "Loss",
  "score_summary": "Cincinnati Bearcats 68.0 (+-2.5=65.5) vs Arizona State Sun Devils 82.0",
  "game_id": "401827640"
}
```

### Pick 8: Hammering Hank - Houston ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31623",
  "capper_name": "Hammering Hank",
  "league": "NCAAB",
  "type": "Moneyline",
  "pick": "Houston ML",
  "line": null,
  "odds": -115,
  "units": 5.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31623",
  "cn": "Hammering Hank",
  "lg": "NCAAB",
  "ty": "Moneyline",
  "p": "Houston",
  "od": null,
  "u": 5.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Loss",
  "score_summary": "Texas Tech Red Raiders 90 - 86 Houston Cougars",
  "game_id": "401827646"
}
```

### Pick 9: Sharp Investments - Jets ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31631",
  "capper_name": "Sharp Investments",
  "league": "NHL",
  "type": "Moneyline",
  "pick": "Jets ML",
  "line": null,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31631",
  "cn": "Sharp Investments",
  "lg": "NHL",
  "ty": "Moneyline",
  "p": "Jets ML",
  "od": null,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "Winnipeg Jets 1 - 5 Detroit Red Wings",
  "game_id": "401803166"
}
```

### Pick 10: Monumental - Mavericks +6
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31630",
  "capper_name": "Monumental",
  "league": "NBA",
  "type": "Spread",
  "pick": "Mavericks +6",
  "line": 6.0,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31630",
  "cn": "Monumental",
  "lg": "NBA",
  "ty": "Spread",
  "p": "Mavericks +6",
  "od": null,
  "u": 1.0,
  "result": "Push",
  "score_summary": "Dallas Mavericks 110.0 (+6.0=116.0) vs Los Angeles Lakers 116.0",
  "game_id": "401810503"
}
```

### Pick 11: Tbsportsbetting - Florida -11.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31628",
  "capper_name": "Tbsportsbetting",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Florida -11.5",
  "line": -11.5,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31628",
  "cn": "Tbsportsbetting",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Florida -11.5",
  "od": null,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "Florida Gators 67.0 (+-11.5=55.5) vs Auburn Tigers 76.0",
  "game_id": "401808193"
}
```

### Pick 12: Tbsportsbetting - Texas -2.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31628",
  "capper_name": "Tbsportsbetting",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Texas -2.5",
  "line": -2.5,
  "odds": -105,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31628",
  "cn": "Tbsportsbetting",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Texas -2.5",
  "od": null,
  "u": 1.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Win",
  "score_summary": "Texas Longhorns 87.0 (+-2.5=84.5) vs Georgia Bulldogs 67.0",
  "game_id": "401808198"
}
```

### Pick 13: Tbsportsbetting - Magic -1.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31628",
  "capper_name": "Tbsportsbetting",
  "league": "NBA",
  "type": "Spread",
  "pick": "Magic -1.5",
  "line": -1.5,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31628",
  "cn": "Tbsportsbetting",
  "lg": "NBA",
  "ty": "Spread",
  "p": "Magic -1.5",
  "od": null,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "Orlando Magic 105.0 (+-1.5=103.5) vs Cleveland Cavaliers 119.0",
  "game_id": "401810501"
}
```

### Pick 14: Tbsportsbetting - Bulls ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31628",
  "capper_name": "Tbsportsbetting",
  "league": "NBA",
  "type": "Moneyline",
  "pick": "Bulls ML",
  "line": null,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31628",
  "cn": "Tbsportsbetting",
  "lg": "NBA",
  "ty": "Moneyline",
  "p": "Bulls ML",
  "od": null,
  "u": 1.0,
  "result": "Win",
  "score_summary": "Chicago Bulls 114 - 111 Boston Celtics",
  "game_id": "401810502"
}
```

### Pick 15: Nicky Cashin - Florida Gators -11
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31627",
  "capper_name": "Nicky Cashin",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Florida Gators -11",
  "line": -11.0,
  "odds": -112,
  "units": 5.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread with odds",
  "id": "31627",
  "cn": "Nicky Cashin",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Florida Gators -11",
  "od": -112,
  "u": 5.0,
  "opponent": "Auburn Tigers",
  "game_date": "2026-01-24",
  "result": "Loss",
  "score_summary": "Florida Gators 67.0 (+-11.0=56.0) vs Auburn Tigers 76.0",
  "game_id": "401808193"
}
```

### Pick 16: DarthFader - Purdue -5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31626",
  "capper_name": "DarthFader",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Purdue -5.5",
  "line": -5.5,
  "odds": -118,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31626",
  "cn": "DarthFader",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Purdue -5.5",
  "od": null,
  "u": 3.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Loss",
  "score_summary": "Purdue Boilermakers 82.0 (+-5.5=76.5) vs Illinois Fighting Illini 88.0",
  "game_id": "401825468"
}
```

### Pick 17: DarthFader - Tcu +3.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31626",
  "capper_name": "DarthFader",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Tcu +3.5",
  "line": 3.5,
  "odds": null,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31626",
  "cn": "DarthFader",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "TCU +3.5",
  "od": null,
  "u": 3.0,
  "result": "Win",
  "score_summary": "TCU Horned Frogs 97.0 (+3.5=100.5) vs Baylor Bears 90.0",
  "game_id": "401827641"
}
```

### Pick 18: DarthFader - Celtics +1
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31626",
  "capper_name": "DarthFader",
  "league": "NBA",
  "type": "Spread",
  "pick": "Celtics +1",
  "line": 1.0,
  "odds": null,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31626",
  "cn": "DarthFader",
  "lg": "NBA",
  "ty": "Spread",
  "p": "Celtics +1",
  "od": null,
  "u": 2.0,
  "result": "Loss",
  "score_summary": "Boston Celtics 111.0 (+1.0=112.0) vs Chicago Bulls 114.0",
  "game_id": "401810502"
}
```

### Pick 19: DarthFader - Kings vs Blues Under 5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31626",
  "capper_name": "DarthFader",
  "league": "NHL",
  "type": "Total",
  "pick": "Kings vs Blues Under 5.5",
  "line": 5.5,
  "odds": -130,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit total with odds",
  "id": "31626",
  "cn": "DarthFader",
  "lg": "NHL",
  "ty": "Total",
  "p": "Kings vs Blues Under 5.5",
  "od": -130,
  "u": 2.0,
  "prop_side": "Under",
  "result": "Loss",
  "score_summary": "Total: 9.0 vs 5.5",
  "game_id": "401803167"
}
```

### Pick 20: DarthFader - Auburn +11.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31626",
  "capper_name": "DarthFader",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Auburn +11.5",
  "line": 11.5,
  "odds": -108,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31626",
  "cn": "DarthFader",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Auburn +11.5",
  "od": null,
  "u": 1.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Win",
  "score_summary": "Auburn Tigers 76.0 (+11.5=87.5) vs Florida Gators 67.0",
  "game_id": "401808193"
}
```

### Pick 21: TMS - NCAAB) Florida ML / (NCAAB) Baylor ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31625",
  "capper_name": "TMS",
  "league": "NCAAB",
  "type": "Parlay",
  "pick": "NCAAB) Florida ML / (NCAAB) Baylor ML",
  "line": null,
  "odds": null,
  "units": 0.5,
  "confidence": 9.0,
  "reasoning": "Explicit parlay",
  "id": "31625",
  "cn": "TMS",
  "lg": "NCAAB",
  "ty": "Parlay",
  "p": "Florida ML / Baylor ML",
  "od": null,
  "u": 0.5,
  "result": "Loss",
  "score_summary": "2 legs"
}
```

### Pick 22: TMS - Colorado -2
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31625",
  "capper_name": "TMS",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Colorado -2",
  "line": -2.0,
  "odds": null,
  "units": 0.5,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31625",
  "cn": "TMS",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Colorado -2",
  "od": null,
  "u": 0.5,
  "result": "Loss",
  "score_summary": "Colorado Buffaloes 86.0 (+-2.0=84.0) vs UCF Knights 95.0",
  "game_id": "401827643"
}
```

### Pick 23: TMS - NCAAB) Purdue ML / (NCAAB) Alabama ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31619",
  "capper_name": "TMS",
  "league": "NCAAB",
  "type": "Parlay",
  "pick": "NCAAB) Purdue ML / (NCAAB) Alabama ML",
  "line": null,
  "odds": -192,
  "units": 0.5,
  "confidence": 9.0,
  "reasoning": "Explicit parlay",
  "id": "31619",
  "cn": "TMS",
  "lg": "NCAAB",
  "ty": "Parlay",
  "p": "Purdue ML / Alabama ML",
  "od": null,
  "u": 0.5,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Loss",
  "score_summary": "2 legs"
}
```

### Pick 24: TMS - Houston ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31619",
  "capper_name": "TMS",
  "league": "NCAAB",
  "type": "Moneyline",
  "pick": "Houston ML",
  "line": null,
  "odds": -115,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31619",
  "cn": "TMS",
  "lg": "NCAAB",
  "ty": "Moneyline",
  "p": "Houston",
  "od": null,
  "u": 1.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Loss",
  "score_summary": "Texas Tech Red Raiders 90 - 86 Houston Cougars",
  "game_id": "401827646"
}
```

### Pick 25: TMS - Texas -2
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31612",
  "capper_name": "TMS",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Texas -2",
  "line": -2.0,
  "odds": -125,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31612",
  "cn": "TMS",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Texas -2",
  "od": null,
  "u": 1.0,
  "result": "Win",
  "score_summary": "Texas Longhorns 87.0 (+-2.0=85.0) vs Georgia Bulldogs 67.0",
  "game_id": "401808198"
}
```

### Pick 26: BeezoWins - Kansas -4.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Kansas -4.5",
  "line": -4.5,
  "odds": null,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Kansas -4.5",
  "od": null,
  "u": 3.0,
  "result": "Win",
  "score_summary": "Kansas Jayhawks 86.0 (+-4.5=81.5) vs Kansas State Wildcats 62.0",
  "game_id": "401827644"
}
```

### Pick 27: BeezoWins - Nebraska -5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Nebraska -5.5",
  "line": -5.5,
  "odds": -108,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Nebraska -5.5",
  "od": null,
  "u": 3.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Win",
  "score_summary": "Nebraska Cornhuskers 76.0 (+-5.5=70.5) vs Minnesota Golden Gophers 57.0",
  "game_id": "401825467"
}
```

### Pick 28: BeezoWins - Texas Tech +1.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Texas Tech +1.5",
  "line": 1.5,
  "odds": -110,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Texas Tech +1.5",
  "od": null,
  "u": 3.0,
  "result": "Win",
  "score_summary": "Texas Tech Red Raiders 90.0 (+1.5=91.5) vs Houston Cougars 86.0",
  "game_id": "401827646"
}
```

### Pick 29: BeezoWins - Purdue -5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Purdue -5.5",
  "line": -5.5,
  "odds": -118,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Purdue -5.5",
  "od": null,
  "u": 2.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Loss",
  "score_summary": "Purdue Boilermakers 82.0 (+-5.5=76.5) vs Illinois Fighting Illini 88.0",
  "game_id": "401825468"
}
```

### Pick 30: BeezoWins - Virginia -6.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Virginia -6.5",
  "line": -6.5,
  "odds": null,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Virginia -6.5",
  "od": null,
  "u": 2.0,
  "result": "Loss",
  "score_summary": "Virginia Cavaliers 80.0 (+-6.5=73.5) vs North Carolina Tar Heels 85.0",
  "game_id": "401820697"
}
```

### Pick 31: BeezoWins - Florida -11.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Florida -11.5",
  "line": -11.5,
  "odds": null,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Florida -11.5",
  "od": null,
  "u": 2.0,
  "result": "Loss",
  "score_summary": "Florida Gators 67.0 (+-11.5=55.5) vs Auburn Tigers 76.0",
  "game_id": "401808193"
}
```

### Pick 32: BeezoWins - Alabama -5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Alabama -5.5",
  "line": -5.5,
  "odds": -102,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Alabama -5.5",
  "od": null,
  "u": 2.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Loss",
  "score_summary": "Alabama Crimson Tide 73.0 (+-5.5=67.5) vs Tennessee Volunteers 79.0",
  "game_id": "401808199"
}
```

### Pick 33: BeezoWins - Georgia Tech +7.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Georgia Tech +7.5",
  "line": 7.5,
  "odds": null,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Georgia Tech +7.5",
  "od": null,
  "u": 2.0,
  "result": "Loss",
  "score_summary": "Georgia Tech Yellow Jackets 63.0 (+7.5=70.5) vs Clemson Tigers 77.0",
  "game_id": "401820690"
}
```

### Pick 34: BeezoWins - Wake Forrest +17.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Wake Forrest +17.5",
  "line": 17.5,
  "odds": -118,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Wake Forrest +17.5",
  "od": null,
  "u": 2.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Loss",
  "score_summary": "Wake Forest Demon Deacons 69.0 (+17.5=86.5) vs Duke Blue Devils 90.0",
  "game_id": "401820689"
}
```

### Pick 35: BeezoWins - Smith: Pts Over 14.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Player Prop",
  "pick": "Smith: Pts Over 14.5",
  "line": 14.5,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit player prop",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Player Prop",
  "p": "Smith (Purdue) over 14.5 pts",
  "od": null,
  "u": 1.0,
  "subject": "Smith",
  "market": "Pts",
  "prop_side": "Over",
  "result": "Loss",
  "score_summary": "Caleb Smith pts: 5.0 vs 14.5",
  "game_id": "401813413"
}
```

### Pick 36: BeezoWins - Toppin (Texas Tech): Pts Over 18.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NCAAB",
  "type": "Player Prop",
  "pick": "Toppin (Texas Tech): Pts Over 18.5",
  "line": 18.5,
  "odds": -115,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit player prop",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NCAAB",
  "ty": "Player Prop",
  "p": "Toppin (Texas Tech) over 18.5 pts",
  "od": null,
  "u": 1.0,
  "subject": "Toppin (Texas Tech)",
  "market": "Pts",
  "prop_side": "Over",
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Pending",
  "score_summary": "Game not found"
}
```

### Pick 37: BeezoWins - Celtics +1.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NBA",
  "type": "Spread",
  "pick": "Celtics +1.5",
  "line": 1.5,
  "odds": null,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NBA",
  "ty": "Spread",
  "p": "Celtics +1.5",
  "od": null,
  "u": 2.0,
  "result": "Loss",
  "score_summary": "Boston Celtics 111.0 (+1.5=112.5) vs Chicago Bulls 114.0",
  "game_id": "401810502"
}
```

### Pick 38: BeezoWins - Oilers ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NHL",
  "type": "Moneyline",
  "pick": "Oilers ML",
  "line": null,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NHL",
  "ty": "Moneyline",
  "p": "Oilers",
  "od": null,
  "u": 1.0,
  "result": "Win",
  "score_summary": "Edmonton Oilers 6 - 5 Washington Capitals",
  "game_id": "401803169"
}
```

### Pick 39: BeezoWins - Lightning ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31622",
  "capper_name": "BeezoWins",
  "league": "NHL",
  "type": "Moneyline",
  "pick": "Lightning ML",
  "line": null,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31622",
  "cn": "BeezoWins",
  "lg": "NHL",
  "ty": "Moneyline",
  "p": "Lightning",
  "od": null,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "Columbus Blue Jackets 8 - 5 Tampa Bay Lightning",
  "game_id": "401803165"
}
```

### Pick 40: McBets - Texas Tech +1.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31621",
  "capper_name": "McBets",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Texas Tech +1.5",
  "line": 1.5,
  "odds": -110,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31621",
  "cn": "McBets",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Texas Tech +1.5",
  "od": -110,
  "u": 1.0,
  "result": "Win",
  "score_summary": "Texas Tech Red Raiders 90.0 (+1.5=91.5) vs Houston Cougars 86.0",
  "game_id": "401827646"
}
```

### Pick 41: McBets - Colorado -3
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31621",
  "capper_name": "McBets",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Colorado -3",
  "line": -3.0,
  "odds": -120,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31621",
  "cn": "McBets",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Colorado -3",
  "od": -120,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "Colorado Buffaloes 86.0 (+-3.0=83.0) vs UCF Knights 95.0",
  "game_id": "401827643"
}
```

### Pick 42: McBets - Oklahoma State +10.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31621",
  "capper_name": "McBets",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Oklahoma State +10.5",
  "line": 10.5,
  "odds": -110,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31621",
  "cn": "McBets",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Oklahoma State +10.5",
  "od": -110,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "Oklahoma State Cowboys 71.0 (+10.5=81.5) vs Iowa State Cyclones 84.0",
  "game_id": "401827645"
}
```

### Pick 43: McBets - Texas Southern ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31621",
  "capper_name": "McBets",
  "league": "NCAAB",
  "type": "Moneyline",
  "pick": "Texas Southern ML",
  "line": null,
  "odds": -105,
  "units": 1.5,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31621",
  "cn": "McBets",
  "lg": "NCAAB",
  "ty": "Moneyline",
  "p": "Texas Southern",
  "od": -105,
  "u": 1.5,
  "result": "Pending",
  "score_summary": "Could not resolve team"
}
```

### Pick 44: McBets - Smu -11
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31621",
  "capper_name": "McBets",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Smu -11",
  "line": -11.0,
  "odds": -120,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31621",
  "cn": "McBets",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "SMU -11",
  "od": -120,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "SMU Mustangs 83.0 (+-11.0=72.0) vs Florida State Seminoles 80.0",
  "game_id": "401820694"
}
```

### Pick 45: TPD - Knicks +1.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31620",
  "capper_name": "TPD",
  "league": "NBA",
  "type": "Spread",
  "pick": "Knicks +1.5",
  "line": 1.5,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31620",
  "cn": "TPD",
  "lg": "NBA",
  "ty": "Spread",
  "p": "Knicks +1.5",
  "od": null,
  "u": 1.0,
  "result": "Win",
  "score_summary": "New York Knicks 112.0 (+1.5=113.5) vs Philadelphia 76ers 109.0",
  "game_id": "401810498"
}
```

### Pick 46: TPD - Kansas State +5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31620",
  "capper_name": "TPD",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Kansas State +5.5",
  "line": 5.5,
  "odds": null,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31620",
  "cn": "TPD",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Kansas State +5.5",
  "od": null,
  "u": 1.0,
  "result": "Win",
  "score_summary": "Kansas Jayhawks 86.0 (+5.5=91.5) vs Kansas State Wildcats 62.0",
  "game_id": "401827644"
}
```

### Pick 47: TPD - Texas ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31620",
  "capper_name": "TPD",
  "league": "NCAAB",
  "type": "Moneyline",
  "pick": "Texas ML",
  "line": null,
  "odds": -162,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31620",
  "cn": "TPD",
  "lg": "NCAAB",
  "ty": "Moneyline",
  "p": "Texas",
  "od": null,
  "u": 1.0,
  "deduction_source": "ESPN_API_BACKFILL",
  "result": "Win",
  "score_summary": "Texas Longhorns 87 - 67 Georgia Bulldogs",
  "game_id": "401808198"
}
```

### Pick 48: Smart Money Sports - Minnesota Golden Gophers +5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Minnesota Golden Gophers +5.5",
  "line": 5.5,
  "odds": -110,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Minnesota Golden Gophers +5.5",
  "od": -110,
  "u": 2.0,
  "opponent": "Nebraska Cornhuskers",
  "game_date": "2026-01-24",
  "result": "Loss",
  "score_summary": "Minnesota Golden Gophers 57.0 (+5.5=62.5) vs Nebraska Cornhuskers 76.0",
  "game_id": "401825467"
}
```

### Pick 49: Smart Money Sports - Texas Longhorns -3
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Texas Longhorns -3",
  "line": -3.0,
  "odds": -105,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Texas Longhorns -3",
  "od": -105,
  "u": 2.0,
  "opponent": "Georgia Bulldogs",
  "game_date": "2026-01-24",
  "result": "Win",
  "score_summary": "Texas Longhorns 87.0 (+-3.0=84.0) vs Georgia Bulldogs 67.0",
  "game_id": "401808198"
}
```

### Pick 50: Smart Money Sports - Rhode Island ML
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Moneyline",
  "pick": "Rhode Island ML",
  "line": null,
  "odds": 110,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit ML",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Moneyline",
  "p": "Rhode Island ML",
  "od": 110,
  "u": 2.0,
  "result": "Win",
  "score_summary": "Rhode Island Rams 74 - 65 George Mason Patriots",
  "game_id": "401828391"
}
```

### Pick 51: Smart Money Sports - Louisville Cardinals -13.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Louisville Cardinals -13.5",
  "line": -13.5,
  "odds": -105,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Louisville Cardinals -13.5",
  "od": -105,
  "u": 2.0,
  "opponent": "Virginia Tech Hokies",
  "game_date": "2026-01-24",
  "result": "Win",
  "score_summary": "Louisville Cardinals 85.0 (+-13.5=71.5) vs Virginia Tech Hokies 71.0",
  "game_id": "401820691"
}
```

### Pick 52: Smart Money Sports - Purdue Boilermakers -6
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Purdue Boilermakers -6",
  "line": -6.0,
  "odds": -105,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Purdue Boilermakers -6",
  "od": -105,
  "u": 2.0,
  "opponent": "Illinois Fighting Illini",
  "game_date": "2026-01-24",
  "result": "Loss",
  "score_summary": "Purdue Boilermakers 82.0 (+-6.0=76.0) vs Illinois Fighting Illini 88.0",
  "game_id": "401825468"
}
```

### Pick 53: Smart Money Sports - San Diego State Aztecs -5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "San Diego State Aztecs -5.5",
  "line": -5.5,
  "odds": -110,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "San Diego State Aztecs -5.5",
  "od": -110,
  "u": 2.0,
  "result": "Loss",
  "score_summary": "San Diego Toreros 73.0 (+-5.5=67.5) vs Santa Clara Broncos 85.0",
  "game_id": "401829215"
}
```

### Pick 54: Smart Money Sports - Memphis Tigers +3
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Memphis Tigers +3",
  "line": 3.0,
  "odds": -110,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Memphis Tigers +3",
  "od": -110,
  "u": 2.0,
  "opponent": "Wichita State Shockers",
  "game_date": "2026-01-24",
  "result": "Loss",
  "score_summary": "Memphis Tigers 59.0 (+3.0=62.0) vs Wichita State Shockers 74.0",
  "game_id": "401828192"
}
```

### Pick 55: Smart Money Sports - Tennessee Volunteers +6
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Tennessee Volunteers +6",
  "line": 6.0,
  "odds": -105,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Tennessee Volunteers +6",
  "od": -105,
  "u": 2.0,
  "opponent": "Alabama Crimson Tide",
  "game_date": "2026-01-24",
  "result": "Win",
  "score_summary": "Tennessee Volunteers 79.0 (+6.0=85.0) vs Alabama Crimson Tide 73.0",
  "game_id": "401808199"
}
```

### Pick 56: Smart Money Sports - Arizona State Sun Devils +2.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31613",
  "capper_name": "Smart Money Sports",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Arizona State Sun Devils +2.5",
  "line": 2.5,
  "odds": -110,
  "units": 2.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31613",
  "cn": "Smart Money Sports",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Arizona State Sun Devils +2.5",
  "od": -110,
  "u": 2.0,
  "opponent": "Cincinnati Bearcats",
  "game_date": "2026-01-24",
  "result": "Pending",
  "score_summary": "Could not resolve team"
}
```

### Pick 57: OutofLineBets - Kentucky -9.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31611",
  "capper_name": "OutofLineBets",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Kentucky -9.5",
  "line": -9.5,
  "odds": -120,
  "units": 3.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31611",
  "cn": "OutofLineBets",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Kentucky -9.5",
  "od": -120,
  "u": 3.0,
  "result": "Loss",
  "score_summary": "Kentucky Wildcats 72.0 (+-9.5=62.5) vs Ole Miss Rebels 63.0",
  "game_id": "401808194"
}
```

### Pick 58: Unknown - Minnesota +5.5
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31609",
  "capper_name": "Unknown",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Minnesota +5.5",
  "line": 5.5,
  "odds": -110,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31609",
  "cn": "Unknown",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Minnesota +5.5",
  "od": -110,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "Minnesota Golden Gophers 57.0 (+5.5=62.5) vs Nebraska Cornhuskers 76.0",
  "game_id": "401825467"
}
```

### Pick 59: Unknown - Texas Tech +2
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31609",
  "capper_name": "Unknown",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Texas Tech +2",
  "line": 2.0,
  "odds": -110,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31609",
  "cn": "Unknown",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Texas Tech +2",
  "od": -110,
  "u": 1.0,
  "result": "Win",
  "score_summary": "Texas Tech Red Raiders 90.0 (+2.0=92.0) vs Houston Cougars 86.0",
  "game_id": "401827646"
}
```

### Pick 60: Unknown - Virginia -6
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31609",
  "capper_name": "Unknown",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Virginia -6",
  "line": -6.0,
  "odds": -120,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31609",
  "cn": "Unknown",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Virginia -6",
  "od": -120,
  "u": 1.0,
  "result": "Loss",
  "score_summary": "Virginia Cavaliers 80.0 (+-6.0=74.0) vs North Carolina Tar Heels 85.0",
  "game_id": "401820697"
}
```

### Pick 61: Unknown - Texas -2
**Raw Text + OCR:**
```text

```
**Parsed Result:**
```json
{
  "message_id": "31609",
  "capper_name": "Unknown",
  "league": "NCAAB",
  "type": "Spread",
  "pick": "Texas -2",
  "line": -2.0,
  "odds": -125,
  "units": 1.0,
  "confidence": 9.0,
  "reasoning": "Explicit spread",
  "id": "31609",
  "cn": "Unknown",
  "lg": "NCAAB",
  "ty": "Spread",
  "p": "Texas -2",
  "od": -125,
  "u": 1.0,
  "result": "Win",
  "score_summary": "Texas Longhorns 87.0 (+-2.0=85.0) vs Georgia Bulldogs 67.0",
  "game_id": "401808198"
}
```

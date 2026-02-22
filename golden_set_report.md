# Verification Report

Accuracy: 70.89%
Correct: 112/158

## Failures

### Message 31621
Text: McBets Afternoon NCAAB  Texas Tech +1.5 (-110) 1u Colorado - 3 (-120) 1u Oklahoma State +10.5 (-110)...
- MISSING: {"pick": "1u - Colorado -2", "odds": null, "units": 1.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "31621", "capper_name": "McBets", "league": "NCAAB", "type": "Spread", "pick": "Texas Tech +1.5", "line": 1.5, "odds": -110, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "31621", "cn": "McBets", "lg": "NCAAB", "ty": "Spread", "p": "Texas Tech +1.5", "od": -110, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "31621", "capper_name": "McBets", "league": "NCAAB", "type": "Spread", "pick": "Colorado -3", "line": -3.0, "odds": -120, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "31621", "cn": "McBets", "lg": "NCAAB", "ty": "Spread", "p": "Colorado -3", "od": -120, "u": 1.0} (Actual)

### Message 31626
Text: DarthFader  Sick Saturday Nuke Whales  3-Unit Fades: Purdue -5.5 TCU +3.5 2-Unit Fades: Celtics +1 K...
- UNEXPECTED: {"message_id": "31626", "capper_name": "DarthFader", "league": "NCAAB", "type": "Spread", "pick": "Purdue -5.5", "line": -5.5, "odds": -110, "units": 3.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "31626", "cn": "DarthFader", "lg": "NCAAB", "ty": "Spread", "p": "Purdue -5.5", "od": null, "u": 3.0} (Actual)

### Message 31633
Text: Porterpicks   TENNESSEE/ALABAMA OVER 167.5 (3-UNITS)...
- MISSING: {"pick": "Tennessee vs Alabama Over 167.5", "odds": null, "units": 1.0, "type": "Total"} (Expected)

### Message 12791
Text: **MARCO D'ANGELO  5% SMU-12**...
- MISSING: {"pick": "5% Smu-12**", "odds": null, "units": 5.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "12791", "capper_name": "Marco D'Angelo", "league": "NCAAB", "type": "Spread", "pick": "Smu -12", "line": -12.0, "odds": null, "units": 5.0, "confidence": 9.0, "reasoning": null, "id": "12791", "cn": "MARCO D'ANGELO", "lg": "NCAAB", "ty": "Spread", "p": "SMU -12", "od": null, "u": 5.0} (Actual)

### Message 12806
Text: UFC 324  👉🏻 BettingWithBush   Paddy “The Baddy” Pimblett -205 4u⭐ Abeta Gautier RD 1 -120 2u⭐ Abeta ...
- MISSING: {"pick": "2u Paddy Pimblett ML", "odds": -136, "units": 2.0, "type": "Moneyline"} (Expected)
- UNEXPECTED: {"message_id": "12806", "capper_name": "BrandonTheProfit", "league": "UFC", "type": "Moneyline", "pick": "DK Hokit ML", "line": null, "odds": null, "units": 2.0, "confidence": 9.0, "reasoning": null, "id": "12806", "cn": "BrandonTheProfit", "lg": "UFC", "ty": "Moneyline", "p": "DK Hokit", "od": null, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "12806", "capper_name": "A11Bets", "league": "UFC", "type": "Moneyline", "pick": "Paddy by Sub", "line": null, "odds": -136, "units": 1.0, "confidence": 9.0, "reasoning": null, "id": "12806", "cn": "A11Bets", "lg": "UFC", "ty": "Moneyline", "p": "Paddy", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "12806", "capper_name": "A11Bets", "league": "UFC", "type": "Moneyline", "pick": "Waldo Cortes ML", "line": null, "odds": -110, "units": 1.0, "confidence": 9.0, "reasoning": null, "id": "12806", "cn": "A11Bets", "lg": "UFC", "ty": "Moneyline", "p": "Waldo Cortes", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "12806", "capper_name": "A11Bets", "league": "UFC", "type": "Moneyline", "pick": "Sean O'Malley ML", "line": null, "odds": null, "units": 0.5, "confidence": 9.0, "reasoning": null, "id": "12806", "cn": "A11Bets", "lg": "UFC", "ty": "Moneyline", "p": "Sean O'Malley", "od": null, "u": 0.5} (Actual)
- UNEXPECTED: {"message_id": "12806", "capper_name": "A11Bets", "league": "TENNIS", "type": "Moneyline", "pick": "Alcaraz ML", "line": null, "odds": -150, "units": 0.5, "confidence": 9.0, "reasoning": null, "id": "12806", "cn": "A11Bets", "lg": "UFC", "ty": "Moneyline", "p": "Alcaraz", "od": null, "u": 0.5} (Actual)
- UNEXPECTED: {"message_id": "12806", "capper_name": "A11Bets", "league": "UFC", "type": "Moneyline", "pick": "Pimblett ML", "line": null, "odds": -230, "units": 3.0, "confidence": 9.0, "reasoning": null, "id": "12806", "cn": "A11Bets", "lg": "UFC", "ty": "Moneyline", "p": "Pimblett", "od": -230, "u": 3.0} (Actual)

### Message 31604
Text: 🔮Provenwinner   1. BULLS ML | TO WIN 2 UNITS (risking 2.3u to win 2u)  1. MURRAY STATE ML | TO WIN 2...
- MISSING: {"pick": "(2 u Alabama -4.5", "odds": -120, "units": 3.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "Miami Hurricanes Over 150.5", "odds": null, "units": 1.0, "type": "Moneyline"} (Expected)
- MISSING: {"pick": "Lightning Over 6.5", "odds": null, "units": 1.0, "type": "Total"} (Expected)
- MISSING: {"pick": "Bruins Over 6.5", "odds": null, "units": 1.0, "type": "Total"} (Expected)
- MISSING: {"pick": "Oilers Over 6.5", "odds": null, "units": 1.0, "type": "Total"} (Expected)
- MISSING: {"pick": "(NCAAB) Team ML parlay Providence / (NHL) Oilers", "odds": null, "units": 1.0, "type": "Parlay"} (Expected)
- MISSING: {"pick": "Providence Over 160.5", "odds": null, "units": 1.0, "type": "Total"} (Expected)
- MISSING: {"pick": "(2u) Texas -2.5", "odds": -110, "units": 2.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "Vanderbilt / Miss State 0160.5", "odds": null, "units": 1.0, "type": "Parlay"} (Expected)
- MISSING: {"pick": "Winthrop vs Presbyterian Over 146.5", "odds": null, "units": 1.0, "type": "Total"} (Expected)
- MISSING: {"pick": "Oklahoma vs Missouri Over 150.5", "odds": null, "units": 1.0, "type": "Total"} (Expected)
- MISSING: {"pick": "North Dakota State vs Oral Roberts Over 142", "odds": null, "units": 1.0, "type": "Total"} (Expected)
- MISSING: {"pick": "Tennessee +6", "odds": null, "units": 1.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "(2 u Utah Byu Over 165.5", "odds": null, "units": 2.0, "type": "Total"} (Expected)
- MISSING: {"pick": "1U Fresno State +4", "odds": -110, "units": 1.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "1U Georgetown vs Providence Under 162 -110", "odds": -110, "units": 1.0, "type": "Total"} (Expected)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Provenwinner", "league": "NBA", "type": "Moneyline", "pick": "Bulls ML", "line": null, "odds": -110, "units": 2.3, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "Provenwinner", "lg": "NBA", "ty": "Moneyline", "p": "BULLS", "od": null, "u": 2.3} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "BettingWithBush", "league": "UFC", "type": "Player Prop", "pick": "Paddy by Sub", "line": null, "odds": 145, "units": 1.5, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "BettingWithBush", "lg": "UFC", "ty": "Player Prop", "p": "Paddy by SUB", "od": 145, "u": 1.5} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "BettingWithBush", "league": "UFC", "type": "Player Prop", "pick": "Paddy round 2", "line": null, "odds": null, "units": 0.5, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "BettingWithBush", "lg": "UFC", "ty": "Player Prop", "p": "Paddy round 2", "od": null, "u": 0.5} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "1/24 cbb plays", "league": "NCAAB", "type": "Spread", "pick": "Auburn +11.5", "line": 11.5, "odds": -110, "units": 1.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "1/24 cbb plays", "lg": "NCAAB", "ty": "Spread", "p": "Auburn +11.5", "od": -110, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "AndersPicks", "league": "NCAAB", "type": "Moneyline", "pick": "Texas ML", "line": null, "odds": -115, "units": 1.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "AndersPicks", "lg": "NCAAB", "ty": "Moneyline", "p": "Texas", "od": -115, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "P4D_Picks4Dayzzz", "league": "NCAAB", "type": "Spread", "pick": "Florida -11", "line": -11.0, "odds": -120, "units": 3.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "P4D_Picks4Dayzzz", "lg": "NCAAB", "ty": "Spread", "p": "Florida -11", "od": -120, "u": 3.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "P4D_Picks4Dayzzz", "league": "NCAAB", "type": "Spread", "pick": "Alabama -5", "line": -5.0, "odds": -120, "units": 3.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "P4D_Picks4Dayzzz", "lg": "NCAAB", "ty": "Spread", "p": "Alabama -5", "od": -120, "u": 3.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "TheGamblingGawd", "league": "NCAAB", "type": "Moneyline", "pick": "Texas ML", "line": null, "odds": -115, "units": 5.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "TheGamblingGawd", "lg": "NCAAB", "ty": "Moneyline", "p": "Texas", "od": null, "u": 5.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "TheGamblingGawd", "league": "NCAAB", "type": "Moneyline", "pick": "Providence ML", "line": null, "odds": null, "units": 1.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "TheGamblingGawd", "lg": "NCAAB", "ty": "Moneyline", "p": "Providence", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "TheGamblingGawd", "league": "NHL", "type": "Moneyline", "pick": "Oilers ML", "line": null, "odds": -175, "units": 1.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "TheGamblingGawd", "lg": "NHL", "ty": "Moneyline", "p": "Oilers", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "ThisGirlBetz", "league": "NHL", "type": "Moneyline", "pick": "Bruins ML", "line": null, "odds": -110, "units": 3.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "ThisGirlBetz", "lg": "NHL", "ty": "Moneyline", "p": "Bruins", "od": -110, "u": 3.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "ThisGirlBetz", "league": "NCAAB", "type": "Spread", "pick": "Purdue -5.5", "line": -5.5, "odds": -110, "units": 3.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "ThisGirlBetz", "lg": "NCAAB", "ty": "Spread", "p": "Purdue -5.5", "od": -110, "u": 3.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Vinny", "league": "NCAAB", "type": "Moneyline", "pick": "Texas Tech +1.5", "line": null, "odds": -115, "units": 2.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "Vinny", "lg": "NCAAB", "ty": "Moneyline", "p": "Texas", "od": null, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Vinny", "league": "NCAAB", "type": "Spread", "pick": "Florida -11.5", "line": -11.5, "odds": null, "units": 2.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "Vinny", "lg": "NCAAB", "ty": "Spread", "p": "Florida -11.5", "od": null, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Vinny", "league": "NCAAB", "type": "Spread", "pick": "Alabama -4.5", "line": -4.5, "odds": -102, "units": 2.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "Vinny", "lg": "NCAAB", "ty": "Spread", "p": "Alabama -4.5", "od": null, "u": 2.0, "deduction_source": "ESPN_API_BACKFILL"} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "PropJoe", "league": "NCAAB", "type": "Spread", "pick": "Cincinnati -1.5", "line": -1.5, "odds": -110, "units": 2.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "PropJoe", "lg": "NCAAB", "ty": "Spread", "p": "Cincinnati -1.5", "od": -110, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "PropJoe", "league": "NCAAB", "type": "Spread", "pick": "North Carolina +7", "line": 7.0, "odds": -110, "units": 1.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "PropJoe", "lg": "NCAAB", "ty": "Spread", "p": "North Carolina +7", "od": -110, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "PropJoe", "league": "NCAAB", "type": "Spread", "pick": "Purdue -5.5", "line": -5.5, "odds": -110, "units": 1.0, "confidence": 9.0, "reasoning": null, "id": "31604", "cn": "PropJoe", "lg": "NCAAB", "ty": "Spread", "p": "Purdue -5.5", "od": -110, "u": 1.0} (Actual)

### Message syn_12789_7190
Text: **BetSharper** 🔥  Synthetic Add: Celtics Over 45...
- MISSING: {"pick": "Synthetic Add: Celtics Over 45", "odds": null, "units": 1.0, "type": "Player Prop"} (Expected)

### Message 10891
Text: **Big Al**  NHL Selections 1* Oilers -175, 10:05 pm  NBA Selections 4* Magic - 1.5, 7:10 pm NCAA Bas...
- MISSING: {"pick": "3* Georgia Tech Under 144", "odds": null, "units": 3.0, "type": "Total"} (Expected)
- MISSING: {"pick": "3* Denver Over 161.5", "odds": null, "units": 3.0, "type": "Total"} (Expected)
- MISSING: {"pick": "3* Oklahoma St Under 163", "odds": null, "units": 3.0, "type": "Total"} (Expected)
- MISSING: {"pick": "5% Cbb Play - Cal St Fullerton Under 172.5", "odds": null, "units": 5.0, "type": "Total"} (Expected)
- UNEXPECTED: {"message_id": "10891", "capper_name": "Kyle Anthony", "league": "UFC", "type": "Moneyline", "pick": "Jean Silva ML", "line": null, "odds": -131, "units": 5.0, "confidence": 9.0, "reasoning": null, "id": "10891", "cn": "Kyle Anthony", "lg": "UFC", "ty": "Moneyline", "p": "Jean Silva", "od": null, "u": 5.0} (Actual)

### Message 31614
Text: HammeringHank  Early CBB Card Villanova +11.5 3U Mississippi State +8 2U South Carolina +10.5 2U...
- MISSING: {"pick": "2U Mississippi State +8", "odds": null, "units": 2.0, "type": "Spread"} (Expected)

### Message syn_12791_8530
Text: **MARCO D'ANGELO  6.0% SMU-13.0**...
- MISSING: {"pick": "0% Smu-13.0**", "odds": null, "units": 0.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "syn_12791_8530", "capper_name": "Marco D'Angelo", "league": "NCAAB", "type": "Spread", "pick": "Smu -13.0", "line": -13.0, "odds": null, "units": 6.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "syn_12791_8530", "cn": "MARCO D'ANGELO", "lg": "NCAAB", "ty": "Spread", "p": "SMU -13.0", "od": null, "u": 6.0} (Actual)

### Message 31608
Text: ThisGirlBetz  SATURDAY UFC324 U.Nurmagomedov via decision - 105 (2u) Derrick Lewis +270 (2u) P.Pimbl...
- MISSING: {"pick": "ML Parlay ML", "odds": null, "units": 1.0, "type": "Moneyline"} (Expected)
- MISSING: {"pick": "(3u) Silva / Silva -110", "odds": null, "units": 3.0, "type": "Parlay"} (Expected)
- MISSING: {"pick": "(2u) ers ML", "odds": -110, "units": 2.0, "type": "Moneyline"} (Expected)
- UNEXPECTED: {"message_id": "31608", "capper_name": "ThisGirlBetz", "league": "UFC", "type": "Moneyline", "pick": "Silva ML", "line": null, "odds": null, "units": 3.0, "confidence": 9.0, "reasoning": "Parlay leg from ML PARLAY Silva/Silva", "id": "31608", "cn": "ThisGirlBetz", "lg": "UFC", "ty": "Moneyline", "p": "Silva", "od": null, "u": 3.0} (Actual)
- UNEXPECTED: {"message_id": "31608", "capper_name": "ThisGirlBetz", "league": "NBA", "type": "Moneyline", "pick": "76ers ML", "line": null, "odds": -110, "units": 2.0, "confidence": 9.0, "reasoning": "Explicit ML", "id": "31608", "cn": "ThisGirlBetz", "lg": "NBA", "ty": "Moneyline", "p": "76ers", "od": -110, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "31608", "capper_name": "ThisGirlBetz", "league": "NBA", "type": "Spread", "pick": "Celtics +1.5", "line": 1.5, "odds": -110, "units": 2.0, "confidence": 9.0, "reasoning": "Explicit spread with odds", "id": "31608", "cn": "ThisGirlBetz", "lg": "NBA", "ty": "Spread", "p": "Celtics +1.5", "od": -110, "u": 2.0} (Actual)

### Message 31622
Text: BeezoWins  NCAA College Basketball Kansas -4.5 (3-Unit) Nebraska -5.5 (3-Unit) Texas Tech +1.5 (3-Un...
- UNEXPECTED: {"message_id": "31622", "capper_name": "BeezoWins", "league": "NCAAB", "type": "Spread", "pick": "Purdue -5.5", "line": -5.5, "odds": -110, "units": 2.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "31622", "cn": "BeezoWins", "lg": "NCAAB", "ty": "Spread", "p": "Purdue -5.5", "od": null, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "31622", "capper_name": "BeezoWins", "league": "NCAAB", "type": "Spread", "pick": "Florida -11.5", "line": -11.5, "odds": null, "units": 2.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "31622", "cn": "BeezoWins", "lg": "NCAAB", "ty": "Spread", "p": "Florida -11.5", "od": null, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "31622", "capper_name": "BeezoWins", "league": "NCAAB", "type": "Spread", "pick": "Alabama -5.5", "line": -5.5, "odds": -102, "units": 2.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "31622", "cn": "BeezoWins", "lg": "NCAAB", "ty": "Spread", "p": "Alabama -5.5", "od": null, "u": 2.0, "deduction_source": "ESPN_API_BACKFILL"} (Actual)
- UNEXPECTED: {"message_id": "31622", "capper_name": "BeezoWins", "league": "NCAAB", "type": "Spread", "pick": "Georgia Tech +7.5", "line": 7.5, "odds": null, "units": 2.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "31622", "cn": "BeezoWins", "lg": "NCAAB", "ty": "Spread", "p": "Georgia Tech +7.5", "od": null, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "31622", "capper_name": "BeezoWins", "league": "NBA", "type": "Spread", "pick": "Celtics +1.5", "line": 1.5, "odds": -110, "units": 2.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "31622", "cn": "BeezoWins", "lg": "NBA", "ty": "Spread", "p": "Celtics +1.5", "od": null, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "31622", "capper_name": "BeezoWins", "league": "NHL", "type": "Moneyline", "pick": "Oilers ML", "line": null, "odds": -175, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "31622", "cn": "BeezoWins", "lg": "NHL", "ty": "Moneyline", "p": "Oilers", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "31622", "capper_name": "BeezoWins", "league": "NHL", "type": "Moneyline", "pick": "Lightning ML", "line": null, "odds": -120, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "31622", "cn": "BeezoWins", "lg": "NHL", "ty": "Moneyline", "p": "Lightning", "od": null, "u": 1.0} (Actual)

### Message syn_1464673962532409456_8516
Text: Zach's Bets NCAAB:  •Texas -1.5 -107 (1.0u)  •Texas Tech +0.5 -109 (0.0u)  •Kansas State +3.5 -105 (...
- UNEXPECTED: {"message_id": "syn_1464673962532409456_8516", "capper_name": "Zach's Bets", "league": "NCAAB", "type": "Moneyline", "pick": "Alabama ML", "line": null, "odds": -119, "units": 8.5, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "syn_1464673962532409456_8516", "cn": "Zach's Bets", "lg": "NCAAB", "ty": "Moneyline", "p": "Alabama", "od": -119, "u": 8.5} (Actual)

### Message syn_1464775667907297465_8027
Text: Jacavalier  CAR ML (50*)  The Hurricanes are one of the most disciplined and structurally sound team...
- MISSING: {"pick": "Car ML", "odds": null, "units": 1.0, "type": "Moneyline"} (Expected)
- MISSING: {"pick": "The Hurricanes are one of the most disciplined and structurally sound teams in the NHL, and their success tonight is heavily tied to their defensive health. A critical statistic to note is that Carolina has not lost a single game in regulation this season when top defenseman Jaccob Slavin is in the lineup, boasting an 7.0--1.0-4.: RE Over 0.5", "odds": 0, "units": 1.0, "type": "Player Prop"} (Expected)
- UNEXPECTED: {"message_id": "syn_1464775667907297465_8027", "capper_name": "Jacavalier", "league": "NHL", "type": "Moneyline", "pick": "Carolina ML", "line": null, "odds": -135, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "syn_1464775667907297465_8027", "cn": "Jacavalier", "lg": "NHL", "ty": "Moneyline", "p": "Carolina", "od": null, "u": 50.0, "deduction_source": "ESPN_API_BACKFILL"} (Actual)

### Message 1464767187876315408
Text: UFC 324  👉🏻 BettingWithBush   Paddy “The Baddy” Pimblett -205 4u⭐ Abeta Gautier RD 1 -120 2u⭐ Abeta ...
- UNEXPECTED: {"message_id": "1464767187876315408", "capper_name": "Porterpicks", "league": "UFC", "type": "Total", "pick": "Pimblett vs Gaethje Over 2.5", "line": 2.5, "odds": null, "units": 3.0, "confidence": 9.0, "reasoning": "Explicit total", "id": "1464767187876315408", "cn": "Porterpicks", "lg": "UFC", "ty": "Total", "p": "Pimblett/Gaethje Over 2.5", "od": null, "u": 3.0, "prop_side": "Over"} (Actual)
- UNEXPECTED: {"message_id": "1464767187876315408", "capper_name": "Porterpicks", "league": "UFC", "type": "Total", "pick": "Figueiredo vs Nurmagomedov Under 2.5 Rounds", "line": 2.5, "odds": null, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit total", "id": "1464767187876315408", "cn": "Porterpicks", "lg": "UFC", "ty": "Total", "p": "Figueiredo/Nurmagomedov Under 2.5 Rounds", "od": null, "u": 1.0, "prop_side": "Under"} (Actual)
- UNEXPECTED: {"message_id": "1464767187876315408", "capper_name": "BettingWithBush", "league": "UFC", "type": "Moneyline", "pick": "Pimblett ML", "line": null, "odds": -205, "units": 4.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "1464767187876315408", "cn": "BettingWithBush", "lg": "UFC", "ty": "Moneyline", "p": "Pimblett", "od": -205, "u": 4.0} (Actual)
- UNEXPECTED: {"message_id": "1464767187876315408", "capper_name": "BettingWithBush", "league": "UFC", "type": "Player Prop", "pick": "Abeta Gautier Itd", "line": null, "odds": null, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit player prop", "id": "1464767187876315408", "cn": "BettingWithBush", "lg": "UFC", "ty": "Player Prop", "p": "Abeta Gautier ITD", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "1464767187876315408", "capper_name": "BettingWithBush", "league": "UFC", "type": "Moneyline", "pick": "Ty Miller ML", "line": null, "odds": null, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "1464767187876315408", "cn": "BettingWithBush", "lg": "UFC", "ty": "Moneyline", "p": "Ty Miller", "od": null, "u": 1.0, "opponent": "Adam Fugitt", "game_date": "2026-01-24"} (Actual)
- UNEXPECTED: {"message_id": "1464767187876315408", "capper_name": "BettingWithBush", "league": "UFC", "type": "Moneyline", "pick": "Waldo Acosta ML", "line": null, "odds": null, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "1464767187876315408", "cn": "BettingWithBush", "lg": "UFC", "ty": "Moneyline", "p": "Waldo Acosta", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "1464767187876315408", "capper_name": "A11Bets", "league": "UFC", "type": "Moneyline", "pick": "Paddy ML", "line": null, "odds": -136, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "1464767187876315408", "cn": "A11Bets", "lg": "UFC", "ty": "Moneyline", "p": "Paddy", "od": null, "u": 1.0} (Actual)

### Message syn_1464617855348900012_6500
Text: Gianni the Greek MMA PICKS  6.0% Odds: Paddy Pimblett -226  2.0% Odds: Song Yadong +179  4.0% Odds: ...
- MISSING: {"pick": "0% Odds: Paddy Pimblett -226", "odds": -226, "units": 0.0, "type": "Player Prop"} (Expected)
- UNEXPECTED: {"message_id": "syn_1464617855348900012_6500", "capper_name": "Gianni the Greek", "league": "UFC", "type": "Moneyline", "pick": "Pimblett ML", "line": null, "odds": -226, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "syn_1464617855348900012_6500", "cn": "Gianni the Greek", "lg": "UFC", "ty": "Moneyline", "p": "Pimblett", "od": -226, "u": 1.0} (Actual)

### Message 1464672333536166059
Text: ..   Ben burns 🔥🔥🔥  3% Connecticut -9.5 4% Memphis +3.5...
- UNEXPECTED: {"message_id": "1464672333536166059", "capper_name": "Ben burns", "league": "NCAAB", "type": "Spread", "pick": "Connecticut -9.5", "line": -9.5, "odds": -102, "units": 3.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "1464672333536166059", "cn": "Ben burns", "lg": "NCAAB", "ty": "Spread", "p": "Connecticut -9.5", "od": null, "u": 3.0, "deduction_source": "ESPN_API_BACKFILL"} (Actual)

### Message syn_1464713392689254565_7726
Text: Monumental  SATURDAY EARLY PREMIUM PLAYS ARE ATTACHED:  BOTH NCAAB  PURDUE -3.0  FLORIDA -10.5 Jon J...
- MISSING: {"pick": "(2 u Florida -11.5", "odds": -120, "units": 3.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "syn_1464713392689254565_7726", "capper_name": "Monumental", "league": "NCAAB", "type": "Spread", "pick": "Florida -10.5", "line": -10.5, "odds": null, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "syn_1464713392689254565_7726", "cn": "Monumental", "lg": "NCAAB", "ty": "Spread", "p": "Florida -10.5", "od": null, "u": 1.0} (Actual)

### Message 1464681029389258763
Text: Pick Don  Knicks +1.5* POD  Kansas State +5.5 Texas ML...
- UNEXPECTED: {"message_id": "1464681029389258763", "capper_name": "Don", "league": "NCAAB", "type": "Spread", "pick": "Kansas State +5.5", "line": 5.5, "odds": null, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit spread", "id": "1464681029389258763", "cn": "Don", "lg": "NCAAB", "ty": "Spread", "p": "Kansas State +5.5", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "1464681029389258763", "capper_name": "Don", "league": "NCAAB", "type": "Moneyline", "pick": "Texas ML", "line": null, "odds": -115, "units": 1.0, "confidence": 9.0, "reasoning": "Explicit moneyline", "id": "1464681029389258763", "cn": "Don", "lg": "NCAAB", "ty": "Moneyline", "p": "Texas", "od": null, "u": 1.0} (Actual)

### Message syn_1464640721440084182_3069
Text: Proven Winner   Risking 1.2 units  Murray St ML  Risking 3.3 units  Chicago Bulls ML Bruins ML -110...
- MISSING: {"pick": "Murray State ML", "odds": null, "units": 1.0, "type": "Moneyline"} (Expected)

### Message 1464771848465154141
Text: Monumental   OWNER'S SELECTION EXCLUSIVE PLAY OF THE DAY IS ATTACHED:  MAVERICKS +6 (NBA)  ====  Ham...
- MISSING: {"pick": "Mavericks +6", "odds": 6, "units": 1.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "California +4.5", "odds": 4.5, "units": 2.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "Cincinnati -2.5", "odds": -2.5, "units": 2.0, "type": "Spread"} (Expected)

### Message 2015123634323439899
Text: Trends (1/4) ➖➖➖➖➖ Game/Time League Signal Play Win% Units Score SameSideCount Verdict Tier 1/24/26 ...
- MISSING: {"pick": "/ 24 / 26 Cbb Steam Buck -3.5-118 56% 55.7 5.8 2 Lean Follow", "odds": null, "units": 1.0, "type": "Parlay"} (Expected)
- MISSING: {"pick": "American Eagles ML", "odds": -118, "units": 5.7, "type": "Spread"} (Expected)
- MISSING: {"pick": "BUCK -3.5", "odds": -110, "units": 5.7, "type": "Spread"} (Expected)

### Message 2015122981853225383
Text: LucrativeMMA (2/3) ➖➖➖➖➖ Cameron Smotherman wins in • round 3 - 0.5 unit bet @ +1600 Umar Nurmagomed...
- MISSING: {"pick": "submission -1.5 unit bet @", "odds": 190, "units": 1.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "2015122981853225383", "capper_name": "LucrativeMMA", "league": "UFC", "type": "Player Prop", "pick": "Umar Nurmagomedov wins by submission", "line": null, "odds": 190, "units": 1.5, "confidence": 9.0, "reasoning": "", "id": "2015122981853225383", "cn": "LucrativeMMA", "lg": "UFC", "ty": "Player Prop", "p": "Umar Nurmagomedov wins by submission", "od": 190, "u": 1.5} (Actual)

### Message 2015120151835004983
Text: Your Daily Capper  2u - Texas ML 1u - Colorado -2 1u - Purdue -4  Parlay Florida -3 + Alabama ML...
- UNEXPECTED: {"message_id": "2015120151835004983", "capper_name": "Your Daily Capper", "league": "NCAAB", "type": "Moneyline", "pick": "Texas ML", "line": null, "odds": -115, "units": 2.0, "confidence": null, "reasoning": "Explicit ML pattern: Texas ML", "id": "2015120151835004983", "cn": "Your Daily Capper", "lg": "NCAAB", "ty": "Moneyline", "p": "Texas", "od": null, "u": 2.0} (Actual)
- UNEXPECTED: {"message_id": "2015120151835004983", "capper_name": "Your Daily Capper", "league": "NCAAB", "type": "Spread", "pick": "Colorado", "line": -2.0, "odds": null, "units": 1.0, "confidence": null, "reasoning": "Explicit spread pattern: Colorado -2", "id": "2015120151835004983", "cn": "Your Daily Capper", "lg": "NCAAB", "ty": "Spread", "p": "Colorado", "od": null, "u": 1.0} (Actual)
- UNEXPECTED: {"message_id": "2015120151835004983", "capper_name": "Your Daily Capper", "league": "NCAAB", "type": "Moneyline", "pick": "Alabama ML", "line": null, "odds": -119, "units": 1.0, "confidence": null, "reasoning": "Explicit ML pattern: Alabama ML", "id": "2015120151835004983", "cn": "Your Daily Capper", "lg": "NCAAB", "ty": "Moneyline", "p": "Alabama", "od": null, "u": 1.0} (Actual)

### Message syn_2015194789558309289_8013
Text: BrandonTheProfit ➖➖➖➖➖ BrandonTheProfit UFC Play 🥋 Hokit/O'Malley MLP +100 (3.0U) FD Hokit vs. Freem...
- MISSING: {"pick": "(3.0U) Hokit / O' Malley MLP +102", "odds": null, "units": 3.0, "type": "Parlay"} (Expected)
- UNEXPECTED: {"message_id": "syn_2015194789558309289_8013", "capper_name": "BrandonTheProfit", "league": "UFC", "type": "Moneyline", "pick": "Hokit ML", "line": null, "odds": null, "units": 1.0, "confidence": null, "reasoning": "Leg of parlay: Hokit ML from 'Hokit/O'Malley MLP'", "id": "syn_2015194789558309289_8013", "cn": "BrandonTheProfit", "lg": "UFC", "ty": "Moneyline", "p": "Hokit", "od": null, "u": null} (Actual)
- UNEXPECTED: {"message_id": "syn_2015194789558309289_8013", "capper_name": "BrandonTheProfit", "league": "UFC", "type": "Moneyline", "pick": "O'Malley ML", "line": null, "odds": null, "units": 2.0, "confidence": null, "reasoning": "Leg of parlay: O'Malley ML from 'Hokit/O'Malley MLP'", "id": "syn_2015194789558309289_8013", "cn": "BrandonTheProfit", "lg": "UFC", "ty": "Moneyline", "p": "O'Malley", "od": null, "u": null} (Actual)

### Message syn_2015203980352376915_9041
Text: ♥️ for more UFC 327 ✅  👉🏻 BrandonTheProfit UFC  Pimblett ML -233 (4.0u) Pimblett/Natalia Silva MLP -...
- MISSING: {"pick": "1.5U Paddy by Sub ML", "odds": 145, "units": 1.5, "type": "Moneyline"} (Expected)
- MISSING: {"pick": "1.5U (TENNIS) Sean O Malley ML / (TENNIS) Alcaraz ML", "odds": null, "units": 1.5, "type": "Parlay"} (Expected)
- UNEXPECTED: {"message_id": "syn_2015203980352376915_9041", "capper_name": "BrandonTheProfit", "league": "UFC", "type": "Moneyline", "pick": "Paddy by Sub", "line": null, "odds": -136, "units": 1.5, "confidence": null, "reasoning": "Leg of parlay: Paddy ML from 'Paddy + Waldo Cortes'", "id": "syn_2015203980352376915_9041", "cn": "BrandonTheProfit", "lg": "UFC", "ty": "Moneyline", "p": "Paddy", "od": null, "u": null} (Actual)

### Message 2015114437271925194
Text: Tokyo Brandon  5% Cal St Fullerton/Cal Poly u172.5...
- MISSING: {"pick": "5% Cal St Fullerton vs Cal Poly Under 172.5", "odds": null, "units": 5.0, "type": "Total"} (Expected)

# Verification Report

Accuracy: 87.34%
Correct: 138/158

## Failures

### Message 12791
Text: **MARCO D'ANGELO  5% SMU-12**...
- MISSING: {"pick": "5% Smu-12**", "odds": null, "units": 5.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "12791", "capper_name": "Marco D'Angelo\n\n5% Smu-12", "league": "UNKNOWN", "type": "Moneyline", "pick": "5% **Marco D'Angelo ML", "odds": null, "units": 5.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "**MARCO D'ANGELO", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "12791", "capper_name": "Marco D'Angelo\n\n5% Smu-12", "league": "NCAAF", "type": "Spread", "pick": "Smu ** -12", "odds": null, "units": 1.0, "line": -12.0, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "SMU -12**", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 12806
Text: UFC 324  👉🏻 BettingWithBush   Paddy “The Baddy” Pimblett -205 4u⭐ Abeta Gautier RD 1 -120 2u⭐ Abeta ...
- UNEXPECTED: {"message_id": "12806", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "1u 315 ML", "odds": null, "units": 1.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "315", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "12806", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "(2U) 102 ML", "odds": null, "units": 2.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "102", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 31604
Text: 🔮Provenwinner   1. BULLS ML | TO WIN 2 UNITS (risking 2.3u to win 2u)  1. MURRAY STATE ML | TO WIN 2...
- MISSING: {"pick": "2U Purdue -2.5", "odds": -110, "units": 2.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Unknown", "league": "UNKNOWN", "type": "Moneyline", "pick": "1.5u Paddy by sub ML", "odds": 145, "units": 1.5, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Paddy by sub +145", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "5U Happy Saturday ML", "odds": null, "units": 5.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Happy Saturday", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Unknown", "league": "NHL", "type": "Player Prop", "pick": "Connor McDavid: Goals Over 0.5", "odds": -110, "units": 1.0, "line": 0.5, "is_over": true, "stat": "Goals", "reasoning": "Extracted via Rule-Based Regex (Anytime Stat)", "_source_text": "Connor McDavid Goal", "confidence": 8.5} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "(2u) Wild ML", "odds": -120, "units": 2.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Wild -120", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "(3u) Houston ML", "odds": -115, "units": 3.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Houston -115", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "31604", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "2U PropJoe ML", "odds": null, "units": 2.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "PropJoe", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 10891
Text: **Big Al**  NHL Selections 1* Oilers -175, 10:05 pm  NBA Selections 4* Magic - 1.5, 7:10 pm NCAA Bas...
- MISSING: {"pick": "4* Minnesota +6, Noon", "odds": null, "units": 4.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "10891", "capper_name": "Big Al", "league": "NBA", "type": "Spread", "pick": "Minnesota , Noon 3* +6", "odds": -115, "units": 1.0, "line": 6.0, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Minnesota +6, Noon 3*", "confidence": 8.5, "extraction_method": "rule_based", "deduction_source": "ESPN_API_BACKFILL"} (Actual)
- UNEXPECTED: {"message_id": "10891", "capper_name": "Big Al", "league": "UNKNOWN", "type": "Moneyline", "pick": "5% **Kyle Anthony UFC ML", "odds": null, "units": 5.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "**Kyle Anthony UFC", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "10891", "capper_name": "Big Al", "league": "UNKNOWN", "type": "Moneyline", "pick": "5% **Tokyo Brandon ** ML", "odds": null, "units": 5.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "**Tokyo Brandon (14-3) **", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 31614
Text: HammeringHank  Early CBB Card Villanova +11.5 3U Mississippi State +8 2U South Carolina +10.5 2U...
- MISSING: {"pick": "2U Mississippi State +8", "odds": null, "units": 2.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "2U South Carolina +10.5", "odds": null, "units": 2.0, "type": "Spread"} (Expected)

### Message 31613
Text: Smart Money Sports  NCAAB Minnesota Golden Gophers +5.5 -110 (2u, 12:00e) Texas Longhorns -3 -105 (2...
- MISSING: {"pick": "(2u Minnesota Golden Gophers +5.5", "odds": -110, "units": 2.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "(2u Memphis Tigers +3", "odds": -110, "units": 2.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "(2u Tennessee Volunteers +6", "odds": -105, "units": 2.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "(2u Arizona State Sun Devils +2.5", "odds": -110, "units": 2.0, "type": "Spread"} (Expected)

### Message 31627
Text: Nicky Cashin  5U CBB 💎 Florida Gators -11 -112 5U...
- UNEXPECTED: {"message_id": "31627", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "5U Nicky Cashin ML", "odds": null, "units": 5.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Nicky Cashin", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message syn_12791_8530
Text: **MARCO D'ANGELO  6.0% SMU-13.0**...
- MISSING: {"pick": "0% Smu-13.0**", "odds": null, "units": 0.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "syn_12791_8530", "capper_name": "Marco D'Angelo\n\n6.0% Smu-13.0", "league": "UNKNOWN", "type": "Moneyline", "pick": "6.0% **Marco D'Angelo ML", "odds": null, "units": 6.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "**MARCO D'ANGELO", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "syn_12791_8530", "capper_name": "Marco D'Angelo\n\n6.0% Smu-13.0", "league": "NCAAF", "type": "Spread", "pick": "Smu ** -13", "odds": null, "units": 1.0, "line": -13.0, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "SMU -13.0**", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 31608
Text: ThisGirlBetz  SATURDAY UFC324 U.Nurmagomedov via decision - 105 (2u) Derrick Lewis +270 (2u) P.Pimbl...
- MISSING: {"pick": "ML Parlay ML", "odds": null, "units": 1.0, "type": "Moneyline"} (Expected)
- UNEXPECTED: {"message_id": "31608", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "(5u) Huge ML", "odds": null, "units": 5.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Huge", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "31608", "capper_name": "Unknown", "league": "Other", "type": "Spread", "pick": "(2u) Celtics +1.5", "odds": -110, "units": 2.0, "line": 1.5, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Celtics +1.5 -110", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 31622
Text: BeezoWins  NCAA College Basketball Kansas -4.5 (3-Unit) Nebraska -5.5 (3-Unit) Texas Tech +1.5 (3-Un...
- UNEXPECTED: {"message_id": "31622", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "Oilers ML", "odds": null, "units": 1.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Oilers ML (1-Unit)", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message syn_1464617855348900012_6500
Text: Gianni the Greek MMA PICKS  6.0% Odds: Paddy Pimblett -226  2.0% Odds: Song Yadong +179  4.0% Odds: ...
- UNEXPECTED: {"message_id": "syn_1464617855348900012_6500", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "6.0% Gianni the Greek Mma Picks ML", "odds": null, "units": 6.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Gianni the Greek MMA PICKS", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 1464672333536166059
Text: ..   Ben burns 🔥🔥🔥  3% Connecticut -9.5 4% Memphis +3.5...
- UNEXPECTED: {"message_id": "1464672333536166059", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "3% Ben burns ML", "odds": null, "units": 3.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Ben burns", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "1464672333536166059", "capper_name": "Unknown", "league": "Other", "type": "Spread", "pick": "4% Connecticut -9.5", "odds": null, "units": 4.0, "line": -9.5, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Connecticut -9.5", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 1464681029389258763
Text: Pick Don  Knicks +1.5* POD  Kansas State +5.5 Texas ML...
- MISSING: {"pick": "Knicks +1.5* Pod", "odds": null, "units": 1.0, "type": "Spread"} (Expected)
- UNEXPECTED: {"message_id": "1464681029389258763", "capper_name": "Unknown", "league": "NBA", "type": "Spread", "pick": "Knicks * +1.5", "odds": null, "units": 1.0, "line": 1.5, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Knicks +1.5*", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "1464681029389258763", "capper_name": "Unknown", "league": "NCAAB", "type": "Spread", "pick": "Kansas State +5.5", "odds": null, "units": 1.0, "line": 5.5, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Kansas State +5.5", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message syn_1464640721440084182_3069
Text: Proven Winner   Risking 1.2 units  Murray St ML  Risking 3.3 units  Chicago Bulls ML Bruins ML -110...
- UNEXPECTED: {"message_id": "syn_1464640721440084182_3069", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "1.2 u Risking ML", "odds": null, "units": 3.3, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Risking", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 1464771848465154141
Text: Monumental   OWNER'S SELECTION EXCLUSIVE PLAY OF THE DAY IS ATTACHED:  MAVERICKS +6 (NBA)  ====  Ham...
- MISSING: {"pick": "Mavericks +6", "odds": 6, "units": 1.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "California +4.5", "odds": 4.5, "units": 2.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "Nevada +8.5", "odds": 8.5, "units": 2.0, "type": "Spread"} (Expected)
- MISSING: {"pick": "Cincinnati -2.5", "odds": -2.5, "units": 2.0, "type": "Spread"} (Expected)

### Message 2015123634323439899
Text: Trends (1/4) ➖➖➖➖➖ Game/Time League Signal Play Win% Units Score SameSideCount Verdict Tier 1/24/26 ...
- MISSING: {"pick": "/ 24 / 26 Cbb Steam Buck -3.5-118 56% 55.7 5.8 2 Lean Follow", "odds": null, "units": 1.0, "type": "Parlay"} (Expected)
- MISSING: {"pick": "American Eagles ML", "odds": -118, "units": 5.7, "type": "Spread"} (Expected)
- MISSING: {"pick": "BUCK -3.5", "odds": -110, "units": 5.7, "type": "Spread"} (Expected)

### Message 2015122981853225383
Text: LucrativeMMA (2/3) ➖➖➖➖➖ Cameron Smotherman wins in • round 3 - 0.5 unit bet @ +1600 Umar Nurmagomed...
- UNEXPECTED: {"message_id": "2015122981853225383", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "vs ML", "odds": -140, "units": 1.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "vs -140", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message syn_2015203980352376915_9041
Text: ♥️ for more UFC 327 ✅  👉🏻 BrandonTheProfit UFC  Pimblett ML -233 (4.0u) Pimblett/Natalia Silva MLP -...
- MISSING: {"pick": "1.5U Paddy by Sub ML", "odds": 145, "units": 1.5, "type": "Moneyline"} (Expected)
- UNEXPECTED: {"message_id": "syn_2015203980352376915_9041", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "(3.0U) 102 ML", "odds": null, "units": 3.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "102", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
- UNEXPECTED: {"message_id": "syn_2015203980352376915_9041", "capper_name": "Unknown", "league": "TENNIS", "type": "Moneyline", "pick": "1.5U Alcaraz ML", "odds": null, "units": 1.5, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Alcaraz ML (-145)", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)

### Message 2015114437271925194
Text: Tokyo Brandon  5% Cal St Fullerton/Cal Poly u172.5...
- UNEXPECTED: {"message_id": "2015114437271925194", "capper_name": "Unknown", "league": "Other", "type": "Moneyline", "pick": "5% Tokyo Brandon ML", "odds": null, "units": 5.0, "line": null, "is_over": null, "stat": null, "reasoning": "Extracted via Rule-Based Regex", "_source_text": "Tokyo Brandon", "confidence": 8.5, "extraction_method": "rule_based"} (Actual)
